%cond1 = icmp ne i64 %iv, -1
%cond2 = icmp ne i64 %iv, -3782
%cond3 = icmp ne i64 %iv, -732864
%cond4 = icmp ne i64 %iv, -874279
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
  br i1 %cond3, label %taken3, label %not_taken3

not_taken2:
  %temp1_2_nt = phi i64 [%temp1_t, %taken1], [%temp1_nt, %not_taken1]
  %temp2_nt = add i64 %temp1_2_nt, 6
  br i1 %cond3, label %taken3, label %not_taken3

taken3:
  %temp2_3 = phi i64 [%temp2_t, %taken2], [%temp2_nt, %not_taken2]
  %temp3_t = add i64 %temp2_3, 3
  br i1 %cond4, label %taken4, label %not_taken4

not_taken3:
  %temp2_3_nt = phi i64 [%temp2_t, %taken2], [%temp2_nt, %not_taken2]
  %temp3_nt = add i64 %temp2_3_nt, 7
  br i1 %cond4, label %taken4, label %not_taken4

taken4:
  %temp3_4 = phi i64 [%temp3_t, %taken3], [%temp3_nt, %not_taken3]
  %temp4_t = add i64 %temp3_4, 1
  br label %merge

not_taken4:
  %temp3_4_nt = phi i64 [%temp3_t, %taken3], [%temp3_nt, %not_taken3]
  %temp4_nt = add i64 %temp3_4_nt, 8
  br label %merge

merge:
  %temp4 = phi i64 [%temp4_t, %taken4], [%temp4_nt, %not_taken4]
  %cx1 = xor i1 %cond1, %cond2
  %cx2 = xor i1 %cond3, %cond4
  %cx = xor i1 %cx1, %cx2
  %cx_val = zext i1 %cx to i64
  %next_op1 = xor i64 %temp4, %cx_val