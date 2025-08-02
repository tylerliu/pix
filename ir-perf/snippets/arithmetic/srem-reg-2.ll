%temp1 = srem i64 %op1, %op1
%op_result = srem i64 %temp1, %op1 
%next_op1 = add i64 %op_result, 1