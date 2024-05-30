#define RVTEST_CODE_BEGIN
#define RVTEST_CODE_END
#define BASEADDR  0xF0000800

#define read_reflect(tmpreg0,tmpreg1,op1,op2,val1,val2,immval,sig_ref,data_ref,index)\
li op1, val1;\
li op2, val2;\
cpp op2, immval(op1);\
sigwto zero, (1 << sig_ref)zero;\
li tmpreg0, data_ref;\
ld tmpreg1, 0(tmpreg0);\
//check test result here



