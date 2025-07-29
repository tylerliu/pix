%temp1 = fadd double %acc, %acc
%temp2 = fadd double %temp1, %temp1
%temp3 = fadd double %temp2, %temp2
%next_acc = fadd double %temp3, %temp3 