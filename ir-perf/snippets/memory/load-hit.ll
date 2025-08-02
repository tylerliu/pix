%seed = mul i64 %iv, 6364136223846793005 ; simple LCG
%idx = and i64 %seed, 255 ; mask to 256 entries
%ptr = getelementptr inbounds [256 x i64], [256 x i64]* @buf_hit, i64 0, i64 %idx
%val = load i64, i64* %ptr
%next_sum = add i64 %sum, %val 