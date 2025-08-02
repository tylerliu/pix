br label %target1

target1:
  br label %target2

target2:
  br label %target3

target3:
  br label %target4

target4:
  br label %merge

merge: 
  %next_op1 = add i64 %op1, 1