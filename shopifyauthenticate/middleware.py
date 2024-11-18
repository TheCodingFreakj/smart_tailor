from django.shortcuts import redirect

def verify_app_installation(request):
    # Extract the HMAC header from the request
    hmac =  request.headers.get("X-Shopify-Hmac-SHA256")
    print(hmac)
    
    # If HMAC is not found or doesn't match, redirect to error page
    if hmac is None:
        return redirect("https://smart-tailor-frnt.onrender.com/error")

    # If valid, return None, meaning no redirect, and continue to the view
    return None



from functools import wraps
from django.http import HttpResponse

# The decorator that wraps the verify_app_installation function
def verify_installation_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Call the function that checks the HMAC and installation
        response = verify_app_installation(request)
        
        # If a response (redirect) is returned, return it immediately
        if response:
            return response
        
        # Otherwise, continue to the actual view
        return func(request, *args, **kwargs)
    
    return wrapper