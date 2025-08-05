; Calculate base seed and add increments for different locations
%base_seed = mul i64 %iv, 6364136223846793005 ; base LCG seed
%seed1 = add i64 %base_seed, 0                ; base + 0 * increment
%seed2 = add i64 %base_seed, %increment1      ; base + 1 * increment  
%seed3 = add i64 %base_seed, %increment2      ; base + 2 * increment
%seed4 = add i64 %base_seed, %increment3      ; base + 3 * increment

; Calculate 4 different indices
%idx1 = and i64 %seed1, 67108863 ; mask to 67108864 entries (512MB working set)
%idx2 = and i64 %seed2, 67108863
%idx3 = and i64 %seed3, 67108863
%idx4 = and i64 %seed4, 67108863

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

; Load from 2 locations
%val1 = load i64, i64* %ptr1
%val2 = load i64, i64* %ptr2

; Sum both loaded values and pointer values
%sum1 = add i64 %val1, %val2
%sum2 = add i64 %val1, %val2
%sum3 = add i64 %ptrval1, %ptrval2
%sum4 = add i64 %ptrval3, %ptrval4
%sum5 = add i64 %sum1, %sum2
%sum6 = add i64 %sum3, %sum4
%sum7 = add i64 %sum5, %sum6
%next_sum = add i64 %sum, %sum7 