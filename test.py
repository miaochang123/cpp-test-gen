import pdb
def constraint_wrap(*argv):
	locals()['cpp_core_number'],locals()['imb_port'] = argv
	pdb.set_trace()
	result = eval('constraint_imb_cppcore')
	print(result)
	return result
def constraint_imb_cppcore(cpp_core_number,imb_port):
	return imb_port ==2 and cpp_core_number ==2
cpp_core_number = 1
imb_port = 2
constraint_wrap(cpp_core_number,imb_port)