%hash = mul i64 %iv, 2654435761
%val1 = lshr i64 %iv, 8
%val1b = and i64 %val1, 1
%cond1 = icmp eq i64 %val1b, 1
%val2 = lshr i64 %iv, 9
%val2b = and i64 %val1, 1
%cond2 = icmp eq i64 %val2b, 1
%val3 = lshr i64 %iv, 10
%val3b = and i64 %val1, 1
%cond3 = icmp eq i64 %val3b, 1
%val4 = lshr i64 %iv, 11
%val4b = and i64 %val1, 1
%cond4 = icmp eq i64 %val4b, 1
br i1 %cond1, label %taken1, label %not_taken1

taken1:
  %temp1 = add i64 %op1, 1
  br label %merge

not_taken1:
  %temp1 = add i64 %op1, 5
  br label %merge

merge:
  %temp2 = add i64 %temp1, 6
  %temp3 = add i64 %temp2, 7
  %temp4 = add i64 %temp3, 8
  %cx1 = xor i1 %cond1, %cond2
  %cx2 = xor i1 %cond3, %cond4
  %cx = xor i1 %cx1, %cx2
  %cx_val = zext i1 %cx to i64
  %next_op1 = xor i64 %temp4, %cx_val