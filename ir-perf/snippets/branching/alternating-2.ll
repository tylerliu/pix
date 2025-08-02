%iv_val = and i64 %iv, 1
%cond1 = icmp eq i64 %iv_val, 1
%cond2 = icmp eq i64 %iv_val, 0
%cond3 = icmp eq i64 %iv_val, 1
%cond4 = icmp eq i64 %iv_val, 0
br i1 %cond1, label %taken1, label %not_taken1

taken1:
  %temp1_t = add i64 %op1, 1
  br i1 %cond2, label %taken2, label %not_taken2

not_taken1:
  %temp1_nt = add i64 %op1, 5
  br i1 %cond2, label %taken2, label %not_taken2

taken2:
  %temp1_2 = phi i64 [%temp1_t, %taken1], [%temp1_nt, %not_taken1]
  %temp2_t = add i64 %temp1_2, 2
  br label %merge

not_taken2:
  %temp1_2_nt = phi i64 [%temp1_t, %taken1], [%temp1_nt, %not_taken1]
  %temp2_nt = add i64 %temp1_2_nt, 6
  br label %merge

merge:
  %temp2 = phi i64 [%temp2_t, %taken2], [%temp2_nt, %not_taken2]
  %temp3 = add i64 %temp2, 7
  %temp4 = add i64 %temp3, 8
  %cx1 = xor i1 %cond1, %cond2
  %cx2 = xor i1 %cond3, %cond4
  %cx = xor i1 %cx1, %cx2
  %cx_val = zext i1 %cx to i64
  %next_op1 = xor i64 %temp4, %cx_val