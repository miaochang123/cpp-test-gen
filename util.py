import ruamel
from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter,SafeRepresenter
import yaml as pyyaml
from constraint import *
from string import Template
import pdb
import random
from encoding import CPP_RS2, CPP_RS1,CPP_IMM12
from enum import Enum
from itertools import *
import argparse
import copy


########################################
all_regs = ['x0','x1','x2','x3','x4','x5','x6','x7','x8',
	    'x9','x10','x11','x12','x13','x14','x15','x16','x17','x18','x19','x20','x21','x22']

rs1_op_set = set(all_regs)
rs2_op_set = set(all_regs)

def constraint(*args):
	rs1,rs2 = args
	return rs1 != rs2

op_sols = []
while any([len(rs1_op_set)]+[len(rs2_op_set)]):
	problem = Problem(MinConflictsSolver())
	problem.addVariable('rs1',list(rs1_op_set))
	problem.addVariable('rs2',list(rs2_op_set))
	problem.addConstraint(constraint,('rs1','rs2'))
	solution = problem.getSolution()
	if(solution is not None):
		rs1_op_set.discard(solution['rs1'])
		rs2_op_set.discard(solution['rs2'])
		op_sols.append(solution)
	problem.reset()

#################################################################################
test_template = Template('''
#include "test_env.h"
RVTEST_CODE_BEGIN
$code
RVTEST_CODE_END'''
)
comment_dict = {}
yaml = YAML(typ="rt")
yaml.default_flow_style = False
yaml.explicit_start = True
yaml.allow_unicode = True
yaml.allow_duplicate_keys = False

safe_yaml = YAML(typ="safe")
safe_yaml.default_flow_style = False
safe_yaml.explicit_start = True
safe_yaml.allow_unicode = True
safe_yaml.allow_duplicate_keys = False

def load_yaml_file(foo):
	try:
		with open(foo, "r") as file:
			return yaml.load(file)
	except ruamel.yaml.constructor.DuplicateKeyError as msg:
		logger = logging.getLogger(__name__)
		error = "\n".join(str(msg).split("\n")[2:-7])
		logger.error(error)
		raise SystemExit

def load_cgf(file):
	with open(file) as fp:
		# Intermediate fix for no aliasing in output cgf.
		# Load in safe mode, dump to string and load in
		# rt mode to support comments.
		# TODO: Find a better way of doing this by
		# overloading functions from the original library
		# representers.
		from io import StringIO
		string_stream = StringIO()
		cgf = dict(safe_yaml.load(fp))
		expand_cgf(cgf)
		return

def rs2val_construct(fields_dict):
	return CPP_RS2(fields_dict['mode_addr'], fields_dict['target_addr'])

def rs1val_construct(fields_dict):
	return CPP_RS1(fields_dict['sig_ref'], fields_dict['len'],fields_dict['data_ref'])

def imm_constructor(fields_dict):
	return CPP_IMM12(fields_dict['action'],fields_dict['token'],fields_dict['target'])

def recursive_get(key,val_dict,stack):
	if key in val_dict.keys():
		return stack + [key]
	else:
		for j in val_dict.keys():
			if isinstance(val_dict[j], dict):
				path = recursive_get(key,val_dict[j],stack + [j])
				if path is not None:
					return path
	return None

#val : val for rs1 or rs2 or imm
#key :string for subscribe field
#path: path to find subscribe field
def get_subscribe_val(val, key, path,val_comment):
	val_map = val_comment[val]
	next_route = path.pop(0)
	#pdb.set_trace()
	if len(path) == 0:
		assert key == next_route, "scribefiled bug!"
		return val_map[next_route]
	else :
		val = get_subscribe_val(val_map[next_route],key,path,val_comment[next_route])
		return val


def subcribe_proc(index,cgf,valset,val_comment):
	subscribe_fields = cgf['template']['subscribe']
	filed_path_dict = {}
	stack = []
	scribe_field_dict = {}
	for i in subscribe_fields:
		path = recursive_get(i,cgf['val'],stack)
		filed_path_dict[i] = path
	for field_key, path  in filed_path_dict.items():
		valset_key = path.pop(0)
		val = get_subscribe_val(valset[valset_key][index],field_key,path,val_comment[valset_key])
		scribe_field_dict[field_key] = val

	return scribe_field_dict

def template(cgf,valset,val_comment):
	global all_regs
	code = []
	valsetpad = {}
	maxlen =0
	template = cgf['template']
	for i  in [op_sols,valset['rs2val'],valset['rs1val'],valset['immval']]:
		if maxlen < len(i):
			maxlen = len(i)
	valset['rs2val'] = pad_list(maxlen,valset['rs2val'])
	valset['rs1val'] = pad_list(maxlen,valset['rs1val'])
	valset['immval'] = pad_list(maxlen,valset['immval'])
	op_solspad = pad_list(maxlen,op_sols)
	tmpregcnt = template['tmpregcnt']
	macro = template['macro']
	for i in range(maxlen):
		scribe_field_dict = {}
		freg_set = set(all_regs)
		scribe_field_dict = subcribe_proc(i,cgf,valset,val_comment)
		code_dict = {'ops':op_solspad[i],'immval':valset['immval'][i],'rs1val':valset['rs1val'][i],'rs2val':valset['rs2val'][i],'index':i}
		code.append(template_instance(tmpregcnt, macro, freg_set,code_dict,scribe_field_dict))
	file = test_template.safe_substitute(code='\n'.join(code))
	print(file)

def test_constructor(fields_dict):
	return 0

def template_instance(tmpregcnt,macro,freg_set,code_dict,scribe_field_dict = None):
	ops = code_dict['ops']
	code_dict.pop('ops')
	freg_set.discard(ops['rs1'])
	freg_set.discard(ops['rs2'])
	macro_tmp = Template(macro)
	temp_map = {'op2':ops['rs2'],'op1':ops['rs1'],'val1':code_dict['rs1val'],'val2':code_dict['rs2val'],'immval':code_dict['immval'],'index':code_dict['index']}
	temp_map = {**temp_map,**scribe_field_dict}
	#transform to hex format
	temp_map = {key: hex(value) if isinstance(value, int) else value for key, value in temp_map.items()}
	for i in range(tmpregcnt):
		temp_map['tmpreg'+str(i)] = list(freg_set)[i]
	code = macro_tmp.safe_substitute(temp_map)
	return code

def pad_list(length,lst):
	padded_list = lst.copy()
	while(len(padded_list) < length):
		padded_list.append(random.choice(lst))
	return padded_list

construct_constraint = lambda val: (lambda x: bool(x in val))

def sub_filed_proc(subname,subfield,comment):
	fieldset = []
	tmp_dict = {}
	constructor = subfield['constructor']
	subfield.pop('constructor')
	for key, content in subfield.items():
		if isinstance(content, dict):
			comment[key] = {}
			tmp_dict[key] = sub_filed_proc(key,content,comment[key])
		else:
			tmp_dict[key] = content
	combinations = [dict(zip(tmp_dict.keys(), values)) for values in product(*tmp_dict.values())]
	for fields_dict in combinations:
		if constructor.startswith("lambda"):
			lam = eval(constructor)
			val = lam(fields_dict)
		else:
			val = eval(constructor)
		fieldset.append(val)
		comment[val] = fields_dict
	'''
	keys = subfield.keys()
	maxlen = 0
	for key in keys:
		if(maxlen < len(valset_dict[key])):
			maxlen = len(valset_dict[key])

	for key in keys:
		tmp_dict[key] = pad_list(maxlen, valset_dict[key])

	valset_dict.update(copy.deepcopy(tmp_dict))

	while any([len(tmp_dict[key]) for key in tmp_dict.keys()]):
		problem = Problem(MinConflictsSolver())
		for key in  tmp_dict.keys():
			problem.addVariable(key,tmp_dict[key])
			problem.addConstraint(construct_constraint(tmp_dict[key]),tuple([key]))
		fields_dict = problem.getSolution()
		print(fields_dict)
		fieldset.append(eval(constructor))
		for key in  tmp_dict.keys():
			tmp_dict[key].remove(fields_dict[key])

	print(fieldset)
	'''
	return fieldset

def expand_cgf(cgf):
	valset ={'rs2val':[],'rs1val':[],'immval':[]}
	val_dict = cgf['val']
	val_comment = {}
	for index,cont in enumerate(['rs2val','rs1val','immval']):
		val_comment[cont] = {}
		tmp_val_dict = val_dict[cont]
		valset[cont] = sub_filed_proc(cont,tmp_val_dict,val_comment[cont])
	template(cgf,valset,val_comment)


parser = argparse.ArgumentParser(description="cpp unit test gen tool")
parser.add_argument('--cgf', '-c', help='cover group file')
args = parser.parse_args()
cgf = args.cgf
if cgf:
	load_cgf("cpp.cgf")
else:
	print("miss cgf para")


