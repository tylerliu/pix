%temp1 = fdiv double %acc, %acc
%temp2 = fdiv double %temp1, %temp1
%temp3 = fdiv double %temp2, %temp2
%next_acc = fdiv double %temp3, %temp3 