%temp1 = fmul double %acc, %acc
%temp2 = fmul double %temp1, %temp1
%temp3 = fmul double %temp2, %temp2
%next_acc = fmul double %temp3, %temp3 