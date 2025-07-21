from django.shortcuts import redirect

# class ProfileCompletionMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         if request.user.is_authenticated:
#             if not request.user.is_profile_complete() or not (request.user.gender and request.user.group and request.user.marital_status):
#                 if request.path != '/complete-profile/':
#                     return redirect('complete_profile')
#         return self.get_response(request)

