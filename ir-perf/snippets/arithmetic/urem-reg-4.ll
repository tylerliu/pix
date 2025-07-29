%temp1 = urem i64 %op1, %op1
%temp2 = urem i64 %temp1, %temp1
%temp3 = urem i64 %temp2, %temp2
%next_op1 = urem i64 %temp3, %temp3 