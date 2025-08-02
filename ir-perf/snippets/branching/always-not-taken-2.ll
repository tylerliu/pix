%cond1 = icmp eq i64 %iv, -1
%cond2 = icmp eq i64 %iv, -3782
%cond3 = icmp eq i64 %iv, -732864
%cond4 = icmp eq i64 %iv, -874279
br i1 %cond1, label %taken1, label %not_taken1

taken1:
  %temp1 = add i64 %op1, 1
  br i1 %cond2, label %taken2, label %not_taken2

not_taken1:
  %temp1 = add i64 %op1, 5
  br i1 %cond2, label %taken2, label %not_taken2

taken2:
  %temp2 = add i64 %temp1, 2
  br label %merge2

not_taken2:
  %temp2 = add i64 %temp1, 6
  br label %merge2

merge2:
  %temp3 = add i64 %temp2, 7
  %temp4 = add i64 %temp3, 8
  %cx1 = xor i1 %cond1, %cond2
  %cx2 = xor i1 %cond3, %cond4
  %cx = xor i1 %cx1, %cx2
  %cx_val = zext i1 %cx to i64
  %next_op1 = xor i64 %temp4, %cx_val