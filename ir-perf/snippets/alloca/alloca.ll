%ptr1 = alloca i64
%ptr1_val = load i64, i64* %ptr1
%ptr2_val = load i64, i64* %ptr1
%ptr3_val = load i64, i64* %ptr1 
%ptr4_val = load i64, i64* %ptr1 
call void @dummy()
%temp1 = xor i64 %op1, %ptr1_val
%temp2 = xor i64 %temp1, %ptr2_val
%temp3 = xor i64 %temp2, %ptr3_val
%next_op1 = xor i64 %temp3, %ptr4_val