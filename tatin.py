#!/usr/bin/env python3
import json, urllib.request, urllib.error, urllib.parse
import os, io, tarfile, shutil, subprocess, base64
import sys, functools, inspect
from bs4 import BeautifulSoup

"""----------------------------
Helpers
----------------------------"""

def pretty(collection, indent=0):
	# return a pretty-formatted string from a list or a dict
	result = ""
	if(isinstance(collection,dict)):
		items = sorted(collection)
	else:
		items = collection
	for item in items:
		result += ' ' * indent 
		if(isinstance(collection,dict)):
			result += str(item) + ' = '
			value = collection[item]
		else:
			value = item
		if(isinstance(value,dict)):
			result += '\n'
			result += pretty(value,indent+1)
		elif(isinstance(value,list)):
			result += pretty(value,indent+1)
		else:
			result += str(value) + '\n'
	return result

def compare_versions(v1, v2):
	# compare to versions strings
	c1 = v1.split('.')
	c2 = v2.split('.')
	for i in range(0,min(len(c1),len(c2))):
		if(c1[i]!=c2[i]):
			try:
				return int(c1[i]) - int(c2[i])
			except ValueError:
				return (c1[i] > c2[i]) - (c1[i] < c2[i])
	return len(c1) - len(c2)

"""----------------------------
Fetch Metadata
----------------------------"""

def soup_from_path(path, use_cache=True):
	# Fetch Helper
	base_url = "http://opensource.apple.com"
	try:
		cachePath = '_tatin/cache'+path.replace('/','_')
		cacheMiss = False
		if(use_cache):
			try:
				data = open(cachePath, 'r').read()
			except FileNotFoundError as e:
				cacheMiss = True
				print('cache miss:'+path)
		if(cacheMiss or not use_cache):
			data = urllib.request.urlopen(base_url+path).read()
			if(use_cache):
				with open(cachePath,'wb') as outfile:
					outfile.write(data)
					outfile.close()
		return BeautifulSoup(data)
	except urllib.error.HTTPError as e:
		print('---'+path+' not found ('+str(e.code)+')')
		return None

def parse_products_and_releases(soup):
	# Get products and releases
	products_releases = {}
	for product_tag in soup.find_all(class_ = "product release-list"):
		product_name = product_tag.find('h3', class_='product-name').string
		products_releases[product_name] = []
		for release in product_tag.find_all("li"):
			name = release.a.get_text(strip=True)
			path = release.a['href']
			products_releases[product_name].insert(0,{'name':name,'path':path})
	return products_releases

def fetch_products_and_releases():
	# Fetch products and releases
	return parse_products_and_releases(soup_from_path(""))


def standard_tarball_path(project,version):
	return '/tarballs/'+project+'/'+project+'-'+version+'.tar.gz'

def special_tarball_path(project,version):
	if(project == 'OpenAL'):
		return 'http://www.openal.org/openal_webstf/downloads/openal-0.0.8.tar.gz'
	else:
		return None
	
def parse_release_versions_and_tarballs(release_soup):
	# Parse releases versions and tarballs
	release_project_versions = {}
	release_projects_tarballs = {}
	for version_tag in release_soup.find_all('tr', class_='project-row'):
		version_string = version_tag.find('td', class_='project-name').get_text(strip=True).split()[0]
		if len(version_string.split('-')) != 2 :
			print('===Wrong version format in'+ version_tag)
		else:
			project = version_string.split('-')[0]
			version = version_string.split('-')[1]
# 			if project=='X11ForMacOSXSource':
# 				project='X11'
			tarball_tag = version_tag.find('td', class_='project-downloads').a
			if tarball_tag != None:
				tarball = tarball_tag['href']
				if tarball != standard_tarball_path(project,version) and tarball != special_tarball_path(project,version):
					print('--- '+project+' version: '+version+' irregular tarball path '+tarball)
				release_project_versions[project]=version
				release_projects_tarballs[project]=tarball
			else:
				print('--- '+project+' version: '+version+' Source not available')
	return release_project_versions, release_projects_tarballs

def fetch_projects_versions_and_tarballs(products_releases):
	# Fetch releases versions and tarballs
	products_releases_versions = products_releases
	projects_tarballs = {}
	for product in sorted(products_releases_versions):
		print('Fetching releases of '+product)
		for release in products_releases[product]:
			print(' Fetching project versions in '+product+' '+release['name']+ '('+release['path']+')')
			release_project_versions, release_projects_tarballs = parse_release_versions_and_tarballs(soup_from_path(release['path']))
			for project in release_project_versions:
				if project not in projects_tarballs:
 					projects_tarballs[project] = {}
				version = release_project_versions[project]
				tarball = release_projects_tarballs[project]
				if version not in projects_tarballs[project]:
					projects_tarballs[project][version] = tarball
				elif projects_tarballs[project][version] != tarball:
					print('--- '+project+' version: '+version+' conflicting tarballs'+projects_tarballs[project][version]+' and '+tarball)
			release['projects_versions'] = release_project_versions
# 			print('Versions:'+json.dumps(release['projects_versions'],indent=2))
	return products_releases_versions, projects_tarballs


def parse_all_projects(source_soup):
	# Parse all projects from /source
	projects = []
	for tag in source_soup.find('div', id='ossmain').table.find_all\
		(lambda tag: tag.name=='a' and tag.parent.name=='td' and tag.string==tag['href']):
		project = tag.string.split('/')[0]
		projects.append(project)
	return projects

def fetch_unreferenced_projects(projects_tarballs):
	# Fetch unreferenced projects from /source
	allprojects = parse_all_projects(soup_from_path('/source/'))
	for project in allprojects:
		if project not in projects_tarballs:
			print('--- '+project+' Unreferenced in product releases')
			projects_tarballs[project] = {}
	return projects_tarballs

def parse_all_versions_of_project(project, project_soup):
	# Get all versions of a project
	versions = []
	if(project_soup is not None):
		for version_tag in project_soup.find('div', id='ossmain').table.find_all(lambda tag: tag.name=='a' and tag.parent.name=='td' and tag.string==tag['href']):
			version_string = version_tag.string.split('/')[0]
			if len(version_string.split('-')) != 2 :
				print('===Wrong version format in'+ str(version_tag))
			else:
				if version_string.split('-')[0]!=project:
	# 				if not(version_string.split('-')[0]=='X11ForMacOSXSource' and project=='X11'):
					print('===Wrong version format in '+ str(version_string))
				version = version_string.split('-')[1]
				versions.append(version)
	return versions

def fetch_unreferenced_versions(projects_tarballs):
	#Fetch unreferenced versions from each project page
	for project in sorted(projects_tarballs):
# 		print('Fetching versions for '+project)
		versions = parse_all_versions_of_project(project, soup_from_path('/source/'+project+'/'))
		for version in versions:
			if version not in projects_tarballs[project]:
				print('--- '+project+' version: '+version+' Unreferenced in product releases')
				projects_tarballs[project][version] = ''
	return projects_tarballs

def fetch_metadata():
	"""Fetch/Parse all project metadata and save it in json files"""
	products_releases = fetch_products_and_releases()
	# print(pretty(products_releases))
	products_releases_versions, projects_tarballs = fetch_projects_versions_and_tarballs(products_releases)
	# print(pretty(products_releases_versions))
	projects_tarballs = fetch_unreferenced_projects(projects_tarballs)
	projects_tarballs = fetch_unreferenced_versions(projects_tarballs)

	print(pretty(projects_tarballs))
	print(pretty(products_releases_versions))

	with open('projects_tarballs.json', 'w') as outfile:
	  json.dump(projects_tarballs, outfile, sort_keys=True,indent=2)

	with open('products_releases_versions.json', 'w') as outfile:
	  json.dump(products_releases_versions, outfile,sort_keys=True,indent=2)

"""----------------------------
Lookup Info
----------------------------"""

products_releases_versions = None
projects_tarballs = None

def load_db():
	global products_releases_versions, projects_tarballs
	if(products_releases_versions is None or projects_tarballs is None):
		products_releases_versions = json.load(open('products_releases_versions.json', 'r'))
		projects_tarballs = json.load(open('projects_tarballs.json', 'r'))

def list_products():
	"""List all the products"""
	load_db()
	return sorted(products_releases_versions.keys())

def list_product_releases(product):
	"""List all the releases of a product"""
	load_db()
	releases = []
	for release in products_releases_versions[product]:
		releases.append(release['name'])
	return releases

def list_release_versions(product,release):
	"""List all the project versions used by a release of a product"""
	load_db()
	for release_info in products_releases_versions[product]:
		if(release_info['name']==release):
			return release_info['projects_versions'] 

def list_projects():
	"""List all the projects"""
	load_db()
	return sorted(projects_tarballs.keys())

def list_project_versions(project):
	"""List all the versions of a project"""
	load_db()
	return projects_tarballs[project]

def list_version_releases(project,version):
	"""List the product releases using a specific project version"""
	load_db()
	products_releases = []
	for product in list_products():
		for release in list_product_releases(product):
			release_versions = list_release_versions(product,release)
			if(project in release_versions):
				if(version==release_versions[project]):
					products_releases.append({'product':product,'release':release})
	return products_releases

"""----------------------------
Fetch tarballs
----------------------------"""

def git_init(repo_dir):
	# helper for git init
	subprocess.Popen(['git', 'init'], cwd=repo_dir, stdout=subprocess.DEVNULL).wait()
	subprocess.Popen(['git', 'config', 'user.email', 'opensource@apple.com'], cwd=repo_dir, stdout=subprocess.DEVNULL).wait()
	subprocess.Popen(['git', 'config', 'user.name', 'opensource.apple.com'], cwd=repo_dir, stdout=subprocess.DEVNULL).wait()

def git_commit_all(repo_dir, message, date, tags):
	# helper for git commit
	env = os.environ
	env['GIT_COMMITTER_DATE']=date
	env['GIT_AUTHOR_DATE']=date
	subprocess.Popen(['git', 'add', '--all'], env=env, cwd=repo_dir, stdout=subprocess.DEVNULL).wait()
	subprocess.Popen(['git', 'commit', '--allow-empty', '--message', message], env=env, cwd=repo_dir, stdout=subprocess.DEVNULL).wait()
	for tag in tags:
		subprocess.Popen(['git', 'tag', tag.replace(' ','_')], env=env, cwd=repo_dir, stdout=subprocess.DEVNULL).wait()

def git_push_to_github(repo_dir, username, password):
	# helper for github API and git push
	print(' pushing %s' % repo_dir)
	repo_name = os.path.basename(repo_dir)
	try:
		uri = 'https://api.github.com/orgs/opensource-apple-repos/repos'
		data = bytes('{"name":"'+repo_name+'"}','utf-8')
		headers = {'Authorization': 'Basic '+base64.b64encode(bytes(username+':'+password,'utf-8')).decode('ascii')}
		urllib.request.urlopen(urllib.request.Request(uri, data, headers)).read()
	except urllib.error.HTTPError as e:
		if(e.code != 422):
			raise e
	
	subprocess.Popen(['git', 'remote', 'add', 'origin', 'git@github.com:opensource-apple-repos/'+repo_name+'.git'], cwd=repo_dir, stdout=subprocess.DEVNULL).wait()
	subprocess.Popen(['git', 'push', 'origin', 'master', '-f'], cwd=repo_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
	subprocess.Popen(['git', 'push', '--tags', '-f'], cwd=repo_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()

def fetch_version_tarball(project,version,url):
	# download a tarball, extract it in the repo and commit it
	tags = []
	for use in list_version_releases(project,version):
		tag = use['product'] + '-' + use['release']
		tags.append(tag.replace(' ','_'))
	tags = sorted(tags,key=functools.cmp_to_key(compare_versions))
	print(' version '+version+' (used in '+str(len(tags))+' releases)')
	if(url==''):
		url = standard_tarball_path(project,version)
		print(' using standard url '+url)
	if(not url.startswith('http://')):
		url = 'http://opensource.apple.com'+url
	for entry in os.listdir(project):
		if(os.path.isdir(project+'/'+entry)):
			if(entry != '.git'):
				shutil.rmtree(project+'/'+entry)
		else:
			os.remove(project+'/'+entry)
	
	try:
		response = urllib.request.urlopen(url)
	except urllib.error.HTTPError as e:
		if(e.code == 404):
			print("tarball not found at "+url)
			return
		else:
			raise e
	tar = tarfile.open(fileobj=io.BytesIO(response.read()))
	for member in tar.getmembers():
		if(not member.isdir()):
			def remove_prefix(text, prefix):
				return text[text.startswith(prefix) and len(prefix):]
			name = remove_prefix(member.name,project+'-'+version+'/') 
			fullpath = project+'/'+name
			os.makedirs(os.path.dirname(fullpath),exist_ok=True)
			try:
				memberfile = tar.extractfile(member)
			except:
				None
			if(memberfile):
				open(fullpath, "wb").write(memberfile.read())
					
	
	last_modified = response.headers.get('Last-Modified')
	git_commit_all(project, version, last_modified, tags)

def fetch_project_tarballs(project):
	"""Fetch all the tarballs for a project and create a local git repo"""
	shutil.rmtree(project,ignore_errors=True)
	os.makedirs(project)
	git_init(project)
	versions = list_project_versions(project)
	print(' '+project+' ('+str(len(versions))+' versions)')
	for version in sorted(versions,key=functools.cmp_to_key(compare_versions)):
		fetch_version_tarball(project, version, versions[version])

def fetch_push_and_cleanup_project(project):
	"""Fetch all the tarballs for a project, create a local git repo, push it on github and erase the local repository"""
	fetch_project_tarballs(project)
	git_push_to_github(project, os.environ['GITHUB_USER'], os.environ['GITHUB_KEY'])
	shutil.rmtree(project,ignore_errors=True)

def auto():
	try:
		projects_auto = json.load(open('projects_auto.json', 'r'))
	except FileNotFoundError:
		projects_auto = {project:False for project in list_projects()}
	all_projects = sorted(projects_auto.keys())
	for project in all_projects:
		if(projects_auto[project] == False):
			print(project + ' ('+ str(all_projects.index(project)) +'/'+ str(len(all_projects)) +')')
			fetch_push_and_cleanup_project(project)
			projects_auto[project] = True
			json.dump(projects_auto, open('projects_auto.json', 'w'), sort_keys=True,indent=2)

"""----------------------------
main
----------------------------"""

def usage(command):
	func = globals()[command]
	params = inspect.getargspec(func).args
	return func.__name__+' '+str(params)+' : '+func.__doc__

def main():
	commands = [
				'fetch_metadata',
				'list_products',
				'list_product_releases',
				'list_release_versions',
				'list_projects',
				'list_project_versions',
				'list_version_releases',
				'fetch_project_tarballs',
				'fetch_push_and_cleanup_project',
				'auto'
				]
	args = sys.argv
	if(len(args)<2 or args[1] not in commands ):
		print('Usage:')
		for command in commands:
			print(usage(command))
		return -1
	if(len(args)>=2):
		command = args[1]
		func = globals()[command]
		func_params = inspect.getargspec(func).args
		if(len(args)-2<len(func_params)):
			print(usage(command))
		else:
			command_args = args[2:2+len(func_params)]
# 			print('calling '+func.__name__+' with args: '+str(command_args))
			res = func(*command_args)
			if(isinstance(res,list) or isinstance(res,dict)):
				print(pretty(res))
			elif(isinstance(res,str)):
				print(res)

main()

