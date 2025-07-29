%conv_result = fpext float %acc2 to double
%next_acc = fadd double %conv_result, 0.0 