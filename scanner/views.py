import requests
from allauth.socialaccount.models import SocialToken
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from github import Github
from django.shortcuts import resolve_url
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess
from django.conf import settings
import hmac
import hashlib
import json

@login_required
def home(request):
    token = SocialToken.objects.get(account__user=request.user, account__provider='github')
    g = Github(token.token)
    user = g.get_user()
    repos = []
    for repo in user.get_repos():
        print(repo.id, repo.full_name)
        repos.append(repo.full_name)
    
    return JsonResponse({'repo':repos})


@login_required
def add_to_scanlist(request,id):
    try:
        token = SocialToken.objects.get(account__user=request.user, account__provider='github')
        g = Github(token.token)
        user = g.get_user()
        repo = g.get_repo(id)
        # webhook_url = request.build_absolute_uri(resolve_url('webhook-endpoint'))
        webhook_url = 'https://discord.com/api/webhooks/1350039952280522822/NINap9sQ2Tm9GsMS-77Ts0WjJm0l2I9VFN0WrdFpktHUh0Ay91FFwGQ_zZC9FSCVYRQY/github'

        config = {
            'url': webhook_url,
            'content_type': 'json'
        }

        # Create the webhook
        hook = repo.create_hook(
            name='web',
            config=config,
            events=['push'],
            active=True
        )

        return JsonResponse({'message': 'Webhook added successfully!', 'hook_id': hook.id})
    except SocialToken.DoesNotExist:
        return JsonResponse({'error': 'GitHub token not found. Please reconnect your GitHub account.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
def clone_or_pull_repo(request, repo_id):
    try:
        token = SocialToken.objects.get(account__user=request.user, account__provider='github')
        g = Github(token.token)

        repo = g.get_repo(int(repo_id))
        clone_url = repo.clone_url
        
        if repo.private:
            clone_url = clone_url.replace("https://", f"https://{token.token}@")

        clone_path = os.path.join(f'{settings.BASE_DIR}/codebase', f'{repo.name}_{repo_id}')

        if os.path.exists(clone_path):
            try:
                subprocess.run(['git', '-C', clone_path, 'pull'], check=True)
                return JsonResponse({"status": "success", "message": f"Repository pulled successfully at {clone_path}"})
            except subprocess.CalledProcessError as e:
                return JsonResponse({"status": "error", "message": f"Failed to pull repository: {str(e)}"}, status=500)
        else:
            subprocess.run(['git', 'clone', clone_url, clone_path], check=True)
            return JsonResponse({"status": "success", "message": f"Repository cloned successfully to {clone_path}"})

    except SocialToken.DoesNotExist:
        return JsonResponse({"status": "error", "message": "GitHub authentication token not found."}, status=403)
    except subprocess.CalledProcessError as e:
        return JsonResponse({"status": "error", "message": f"Git command failed: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
@csrf_exempt
def github_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    payload = json.loads(request.body)
    print(payload)
    return JsonResponse({"status": "ok"})

