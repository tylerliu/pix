%seed = mul i64 %iv, 6364136223846793005 ; simple LCG
%idx = and i64 %seed, 67108863 ; mask to 67108864 entries
%ptr = getelementptr inbounds [67108864 x i64], [67108864 x i64]* @buf_miss, i64 0, i64 %idx
store i64 %iv, i64* %ptr
store i64 %iv, i64* %ptr
%sum1 = add i64 %sum, %iv
%next_sum = add i64 %sum1, %iv 