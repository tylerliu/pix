%shuffled1 = shufflevector <4 x i32> %vec_val, <4 x i32> %vec_val, <4 x i32> <i32 3, i32 2, i32 1, i32 0>
%shuffled2 = shufflevector <4 x i32> %shuffled1, <4 x i32> %shuffled1, <4 x i32> <i32 0, i32 1, i32 2, i32 3>
%shuffled3 = shufflevector <4 x i32> %shuffled2, <4 x i32> %shuffled2, <4 x i32> <i32 1, i32 0, i32 3, i32 2>
%shuffled4 = shufflevector <4 x i32> %shuffled3, <4 x i32> %shuffled3, <4 x i32> <i32 2, i32 3, i32 0, i32 1> 