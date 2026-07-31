from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
def chat_message_handler(request):
    user_input = request.data.get('message')
    
    if not user_input:
        return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    # --- Place your Claude API call or database search logic here ---
    # backend_ai_reply = call_claude_api(user_input)
    backend_ai_reply = f"Received your order request: '{user_input}'. Processing..."
    
    return Response({
        "reply": backend_ai_reply,
        "status": "success"
    }, status=status.HTTP_200_OK)