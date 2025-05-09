import requests
from allauth.socialaccount.models import SocialToken
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from github import Github
from django.shortcuts import resolve_url,render, redirect
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess
from django.conf import settings
import json
from .models import ScanList, Reports
import threading
import shutil
import re


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
    report.commit_id = commit_id
    report.commit_url = commit_url
    report.save()
    print('dir removal')
    with open(os.path.join(f'{settings.BASE_DIR}/reports',f'{report.id}.html'), 'r', encoding='utf-8') as file:
        content = file.read()
    # Replace the CSS block
    updated_content = re.sub(
        r'header\s*{\s*background-color:\s*#F1F4FF;\s*}',
        'header {\n display: None;\n}',
        content
    )
    # Save the updated HTML back to file
    with open(os.path.join(f'{settings.BASE_DIR}/reports',f'{report.id}.html'), 'w', encoding='utf-8') as file:
        file.write(updated_content)
    return

@login_required
def home(request):
    token = SocialToken.objects.get(account__user=request.user, account__provider='github')
    g = Github(token.token)
    repos = []
    scan_list = ScanList.objects.filter(user = request.user)
    for repo in scan_list:
        i = g.get_repo(int(repo.repo_id))
        r = Reports.objects.filter(repo = repo).first()
        repos.append({
            'name':i.full_name,
            'id': repo.id,
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

        scan_list = ScanList(repo_id = id, token = token.token,  user=request.user)
        scan_list.save()

        return redirect('reports',scan_list.id)
    except SocialToken.DoesNotExist:
        return JsonResponse({'error': 'GitHub token not found. Please reconnect your GitHub account.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
def add_list(request):
    token = SocialToken.objects.get(account__user=request.user, account__provider='github')
    g = Github(token.token)
    user = g.get_user()
    repos = []
    for repo in user.get_repos():
        if not ScanList.objects.filter(repo_id=repo.id).exists():
            print(repo.id, repo.full_name)
            repos.append({
                'name':repo.full_name,
                'id': repo.id,
            })
    return render(request,'add_list.html',context={'repos':repos})

@csrf_exempt
def github_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    payload = json.loads(request.body)
    repo_id = payload['repository']['id']
    t = threading.Thread(target=scan_repo,args=(repo_id,))
    t.start()
    return JsonResponse({"status": "ok"})

@login_required
def reports(request,id):
    scan_list = ScanList.objects.get(id = id)
    r = Reports.objects.filter(repo = scan_list).order_by('-datetime')
    media_url = settings.MEDIA_URL
    return render(request,'reports.html',context={'media_url':media_url,'reports':r})
