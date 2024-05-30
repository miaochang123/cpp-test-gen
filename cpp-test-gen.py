import argparse
import ruamel
from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter,SafeRepresenter
import yaml as pyyaml
import pdb
from constraint import *
from string import Template

def constraint_imb_cppcore(cpp_core_number,imb_port):
	return imb_port %16 ==  cpp_core_number

class cpp_template:
	def __init__(self,cgf):
		self.template = cgf['template']
		cgf['val_fields'].pop('constraints',None)
		self.fields = cgf['val_fields'].keys()
		self.test_template = Template('''
						#include "test_env.h"
						RVTEST_CODE_BEGIN
						$code
						RVTEST_CODE_END'''
						)
		self.macro = self.template['macro']
		self.tmpregcnt = self.template['tmpregcnt']

	def code_create(self,val_sols,op_sols):
		for i,value in  enumerate(val_sols):
			pdb.set_trace()
			print(val_sols[i])
			print(op_sols[i])
		return 0


class cpp_instruction:
	def __init__(self,cgf_dicts):
		self.constraints = cgf_dicts.pop('constraints', None)
		self.fields = cgf_dicts

	def get_val_sols(self):
		problem = Problem()
		for key, value in  self.fields.items():
			problem.addVariable(key,value)
		for key,value in  self.constraints.items():
			def constraint_wrap(*argv):
				result = eval(key)(*argv)
				return result
			problem.addConstraint(constraint_wrap,tuple(value))
		solutions = problem.getSolutions()
		for i in solutions:
			print(i)
		return solutions




def load_cgf(file):
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
		cpp_ins_meta = cpp_instruction(cgf['val_fields'])
		solutions = cpp_ins_meta.get_val_sols()
		code_template = cpp_template(cgf)
		return solutions,code_template


def get_register_set():
	all_regs = ['x0','x1','x2','x3','x4','x5','x6','x7','x8',
	    	    'x9','x10','x11','x12','x13','x14','x15','x16',
		    'x17','x18','x19','x20','x21','x22','x23','x24',
		    'x25','x26','x27','x28','x29','x30','x31','x32']
	rs1_op_set = set(all_regs)
	rs2_op_set = set(all_regs)
	op_sols = []

	def constraint(*args):
		rs1,rs2 = args
		return rs1 != rs2

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
	return op_sols




def main():
	parser = argparse.ArgumentParser(description="cpp unit test gen tool")
	parser.add_argument('--cgf', '-c', help='cover group file')
	args = parser.parse_args()

	if not args.cgf:
		print("miss cgf para")
		return

	val_sols, code_template = load_cgf(args.cgf)
	op_sols = get_register_set()
	code_template.code_create(op_sols,val_sols)


if __name__ == "__main__":
    main()

