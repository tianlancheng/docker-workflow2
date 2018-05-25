import docker
from config import Config
import json
import time
import datetime
from bson.objectid import ObjectId

dockerClient = docker.DockerClient(base_url = 'unix://var/run/docker.sock', version = Config.DOCKER_VERSION)

from pymongo import MongoClient
client = MongoClient('localhost', 27017)
db = client.dagdb

def start_action(taskId,action):
	print("start action:" + taskId + "-" + action['id'])
	operatorName = action['componentId']
	operator = db.operators.find_one({'operatorName': operatorName})
	if not operator:
		raise Exception('not find operator')  

	paramaters=''
	if(operator.get('parameters')):
		for paramater in operator.get('parameters'):
			value=action['paramSetting'].get(paramater['key'])
			paramaters=paramaters+json.dumps(value)+' '
	
	print 'paramaters: ',paramaters

	restart = docker.types.RestartPolicy(condition = 'none', delay = 0, max_attempts = 0, window = 0)
	dockerClient.services.create(image=operatorName.lower(), 
		name=taskId+'-'+action['id'],
		mounts=["nfs-volume:/nfs-data:rw"],
		command=action['script']+' '+paramaters,
		restart_policy=restart,
		labels={'task':'action',"taskId":taskId,"actionId":action['id']})

# data={
# 	"type":"",
# 	"taskId":"",
# 	"actionId":"",
# 	"error":"",
# 	"executeTime":""
# }
def handle_action(data):
	taskId = data['taskId']
	task = db.workflow_tasks.find_one({'_id':ObjectId(taskId)})
	if not task:
		return

	actionId=data['actionId']
	if data['error']:
		task['actions'][actionId]['state'] = 'error'
		task['actions'][actionId]['error'] = data['error']
		task['state'] = 'error'
		db.workflow_tasks.save(task)
		return


	task['actions'][actionId]['state'] = 'finnish'
	task['actions'][actionId]['executeTime'] = data['executeTime']
	task['finishNum'] = task['finishNum']+1
	if task['finishNum'] == task['actionNum']:
		task['state']='finish'
		task['endTime']=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
		db.workflow_tasks.save(task)
		return

	if task['isStop']:
		task['state'] = 'stoped'
		task['actions'][actionId]['state'] = 'stoped'
		db.workflow_tasks.save(task)
		return

	nextActions = task['actions'][actionId]['nextActions']
	for nextActionName in nextActions:
		nextAction = task['actions'][nextActionName]
		waitNum = nextAction['waitNum']-1
		task['actions'][nextActionName]['waitNum'] = waitNum
		if waitNum == 0:
			try:
				start_action(taskId,nextAction)
			except Exception,e:
				print(e)
				task['state'] = 'error'
				task['actions'][nextActionName]['state'] = 'error'
				task['actions'][nextActionName]['error'] = str(e)			
				break
			else:
				task['actions'][nextActionName]['state'] = 'running'
	db.workflow_tasks.save(task)


def cycle():
	while(True):
		services = dockerClient.services.list(filters = {"label":"task"})
		for service in services:
			tasks = service.tasks()
			isFinish = True
			error = None
			for task in tasks:
				if task['DesiredState'] == 'running':
					isFinish = False
				if task['Status']['State'] == 'failed':
					error = task['Status']['Err']

			if isFinish:
				labels = service.attrs['Spec']['Labels']
				createTime = service.attrs['CreatedAt'][0:26]+'Z'
				createTime = datetime.datetime.strptime(createTime, '%Y-%m-%dT%H:%M:%S.%fZ')
				nowTime = datetime.datetime.utcnow()
				executeTime = (nowTime-createTime).total_seconds()
				data={
					"type": "action",
					"taskId": labels['taskId'],
					"actionId": labels['actionId'],
					"error": error,
					"executeTime": executeTime
				}
				print(data)
				handle_action(data)
				service.remove()
		time.sleep(1)

if __name__ == '__main__':
	print 'monitoring ...'
	cycle()


