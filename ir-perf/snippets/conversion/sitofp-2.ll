%input = phi i64 [42, %entry], [%next_input, %loop]
%temp1 = add i64 %input, 1
%temp2 = add i64 %temp1, 1
%temp3 = add i64 %temp2, 1
%result1 = sitofp i64 %input to double
%result2 = sitofp i64 %temp1 to double
%result1_int = fptosi double %result1 to i64
%result2_int = fptosi double %result2 to i64
%result1_int2 = fptosi double %result1 to i64
%result2_int2 = fptosi double %result2 to i64
%sum1 = add i64 %sum, %result1_int
%sum2 = add i64 %sum1, %result2_int
%sum3 = add i64 %sum2, %result1_int2
%next_sum = add i64 %sum3, %result2_int2
%diff = sub i64 %temp2, %temp1
%next_input = add i64 %temp3, %diff 