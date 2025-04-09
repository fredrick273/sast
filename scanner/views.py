import requests
from allauth.socialaccount.models import SocialToken
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from github import Github
from django.shortcuts import resolve_url,render
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess
from django.conf import settings
import json
from .models import ScanList, Reports
import threading
import shutil


# Helper function
# bearer scan ./juice-shop/ --format html --output report.html

def scan_repo(repo_id):
    scan_list = ScanList.objects.get(repo_id = repo_id)
    g = Github(scan_list.token)
    repo = g.get_repo(int(repo_id))
    clone_url = repo.clone_url
    commits = repo.get_commits(sha=repo.default_branch)
    latest_commit = commits[0]
    commit_id = latest_commit.sha
    commit_url = latest_commit.html_url
    print(commit_id,commit_url)
    if repo.private:
        clone_url = clone_url.replace("https://", f"https://{scan_list.token}@")
    clone_path = os.path.join(f'{settings.BASE_DIR}/codebase', f'{repo.name}_{repo_id}')
    if os.path.exists(clone_path):
        print("Error: Path is in use")
        return
    report = Reports(repo = scan_list)
    report.save()
    subprocess.run(['git', 'clone', clone_url, clone_path], check=True)
    print('clone done')
    subprocess.run(['bearer', 'scan', clone_path, '--format', 'html', '--output',os.path.join(f'{settings.BASE_DIR}/reports',f'{report.id}.html')])
    shutil.rmtree(clone_path)
    report.analysis_done = True
    print('dir removal')
    return

@login_required
def home(request):
    token = SocialToken.objects.get(account__user=request.user, account__provider='github')
    g = Github(token.token)
    user = g.get_user()
    repos = []
    scan_list = ScanList.objects.filter(token = token.token)
    print(scan_list)
    print(token.token, ScanList.objects.all().first().token)
    for repo in scan_list:
        i = g.get_repo(int(repo.repo_id))
        r = Reports.objects.filter(repo = repo).first()
        repos.append({
            'name':i.full_name,
            'id': i.id,
            'url': i.html_url,
            'time': r.datetime if r else None
        })

    return render(request, 'home.html',context = {'repos':repos})


@login_required
def add_to_scanlist(request,id):
    try:
        token = SocialToken.objects.get(account__user=request.user, account__provider='github')
        g = Github(token.token)
        user = g.get_user()
        repo = g.get_repo(id)
        webhook_url = request.build_absolute_uri(resolve_url('github_endpoint'))

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

        scan_list = ScanList(repo_id = id, token = token.token)
        scan_list.save()

        return JsonResponse({'message': 'Webhook added successfully!', 'hook_id': hook.id})
    except SocialToken.DoesNotExist:
        return JsonResponse({'error': 'GitHub token not found. Please reconnect your GitHub account.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
def github_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    payload = json.loads(request.body)
    repo_id = payload['repository']['id']
    t = threading.Thread(target=scan_repo,args=(repo_id,))
    t.start()
    return JsonResponse({"status": "ok"})

