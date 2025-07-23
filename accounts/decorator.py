from django.shortcuts import render
from django.http import HttpResponseForbidden,HttpResponse
from functools import wraps


def group_required(required_groups):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return render(request, "page_404.html")
            
            user_group = request.user.group 
            
            if user_group and user_group.title in required_groups:
                return view_func(request, *args, **kwargs)
            return render(request, "page_404.html")
        return wrapped_view
    return decorator


