; strided access
%seed1 = phi i64 [0, %entry], [%next_seed1, %loop]
%seed2 = add i64 %seed1, 128
%seed3 = add i64 %seed2, 128
%seed4 = add i64 %seed3, 128
%next_seed1 = add i64 %seed4, 128

; Calculate 4 different indices
%idx1 = and i64 %seed1, 131071 ; mask to 131072 entries (1MB working set)
%idx2 = and i64 %seed2, 131071
%idx3 = and i64 %seed3, 131071
%idx4 = and i64 %seed4, 131071

; Create 4 different pointers
%ptr1 = getelementptr inbounds [67108864 x i64], [67108864 x i64]* @buf, i64 0, i64 %idx1
%ptr2 = getelementptr inbounds [67108864 x i64], [67108864 x i64]* @buf, i64 0, i64 %idx2
%ptr3 = getelementptr inbounds [67108864 x i64], [67108864 x i64]* @buf, i64 0, i64 %idx3
%ptr4 = getelementptr inbounds [67108864 x i64], [67108864 x i64]* @buf, i64 0, i64 %idx4

; Convert pointers to integers for summing
%ptrval1 = ptrtoint i64* %ptr1 to i64
%ptrval2 = ptrtoint i64* %ptr2 to i64
%ptrval3 = ptrtoint i64* %ptr3 to i64
%ptrval4 = ptrtoint i64* %ptr4 to i64

; Store to 4 different locations
store i64 %iv, i64* %ptr1
store i64 %iv, i64* %ptr2
store i64 %iv, i64* %ptr3
store i64 %iv, i64* %ptr4

; Sum only pointer values (stores don't return values)
%sum1 = add i64 %ptrval1, %ptrval2
%sum2 = add i64 %ptrval3, %ptrval4
%sum3 = add i64 %sum1, %sum2
%next_sum = add i64 %sum, %sum3 