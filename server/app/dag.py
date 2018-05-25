# -*- coding: utf-8 -*-
from flask import Blueprint,request
from flask import jsonify
from base import require_args,require_json
import re,json,os
import datetime
from app import app,mongo
from bson.objectid import ObjectId
import tools
import datetime

import docker
dockerClient=docker.DockerClient(base_url='unix://var/run/docker.sock', version=app.config['DOCKER_VERSION'])

dag = Blueprint('dag',__name__)

@dag.route('/workflow',methods=['POST'])
@require_json('workflowName')
def add_workflow():
	data = json.loads(request.get_data())
	try:
		parse(data)
	except Exception,e:
		print(e)
		return jsonify(status=400, msg='parse error', data=None), 400
	res=mongo.db.operators.find_one({'workflowName':data['workflowName']},{'_id':1})
	if res:
		return jsonify(status=400, msg='workflowName already exists', data=None), 400

	data["cteateTime"]=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
	id=mongo.db.workflows.insert(data)
	res=mongo.db.workflows.find_one({'_id':id})
	res['_id']=str(res['_id'])
	return jsonify(status=200, msg='success', data=res), 200

@dag.route('/workflows',methods=['GET'])
@require_args('currentPage','pageSize')
def get_workflows():
	currentPage=int(request.args.get("currentPage"))
	pageSize=int(request.args.get("pageSize"))
	skip=(currentPage-1)*pageSize
	filters=request.args.get('filters')
	if not filters:
		filters={}
	else:
		filters=json.loads(filters)
	results=mongo.db.workflows.find(filters).sort("cteateTime",-1).skip(skip).limit(pageSize)
	data=[]
	for result in results:
		result['_id']=str(result['_id'])
		data.append(result)  
	return jsonify(status=200, msg='success', data=data), 200

@dag.route('/workflow/<id>',methods=['GET'])
def get_workflow(id):
	res=mongo.db.workflows.find_one({'_id':ObjectId(id)})
	if not res:
		return jsonify(status=400, msg='can not find workflow', data=None), 400
	res['_id']=str(res['_id'])
	return jsonify(status=200, msg='success', data=res), 200

@dag.route('/workflow/<id>',methods=['PUT'])
def update_workflow(id):
	data = json.loads(request.get_data())
	res=mongo.db.workflows.find_one({'_id':ObjectId(id)},{'_id':1})
	if not res:
		return jsonify(status=400, msg='can not find workflow', data=None), 400
	mongo.db.workflows.update({"_id":ObjectId(id)},{"$set":data})
	res=mongo.db.workflows.find_one({'_id':ObjectId(id)})
	res['_id']=str(res['_id'])
	return jsonify(status=200, msg='success', data=res), 200

@dag.route('/workflow/<id>',methods=['DELETE'])
def delete_workflow(id):
	res=mongo.db.workflows.find_one({'_id':ObjectId(id)},{'_id':1})
	if not res:
		return jsonify(status=400, msg='can not find workflow', data=None), 400
	mongo.db.workflows.remove({'_id':ObjectId(id)})
	return jsonify(status=200, msg='success', data=None), 200




@dag.route('/workflow/<workflowId>/start',methods=['POST'])
def start_workflow(workflowId):
	workflow=mongo.db.workflows.find_one({'_id':ObjectId(workflowId)})
	if not workflow:
		return jsonify(status=400, msg='can not find workflow', data=None), 400
	try:
		task=parse(workflow)
	except Exception,e:
		print(e)
		return jsonify(status=400, msg='workflow parse error', data=None), 400

	task['workflowId']=str(workflow['_id'])
	del workflow['_id']
	
	id=mongo.db.workflow_tasks.insert(task)

	taskId=str(id)

	task['startTime']=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')

	#start begin actions
	for k in task['actions']:
		action=task['actions'][k]
		if action['waitNum']==0:
			try:
				start_action(taskId,action)
			except Exception,e:
				print(e)
				task['state'] = 'error'
				task['actions'][k]['state'] = 'error'
				task['actions'][k]['error'] = str(e)
				mongo.db.workflow_tasks.update({"_id":ObjectId(id)},{"$set":task})
				return jsonify(status=400, msg='error', data=str(e)), 400
			else:
				task['actions'][k]['state']='running'
	
	mongo.db.workflow_tasks.update({"_id":ObjectId(id)},{"$set":task})
	return jsonify(status=200, msg='success', data={"taskId":str(id)}), 200



@dag.route('/workflow_tasks',methods=['GET'])
@require_args('currentPage','pageSize')
def get_workflow_tasks():
	currentPage=int(request.args.get("currentPage"))
	pageSize=int(request.args.get("pageSize"))
	skip=(currentPage-1)*pageSize
	filters=request.args.get('filters')
	if not filters:
		filters={}
	else:
		filters=json.loads(filters)
	results=mongo.db.workflow_tasks.find(filters).sort("cteateTime",-1).skip(skip).limit(pageSize)
	data=[]
	for result in results:
		result['_id']=str(result['_id'])
		data.append(result)  
	return jsonify(status=200, msg='success', data=data), 200

@dag.route('/workflow_task/<id>',methods=['GET'])
def get_workflow_task(id):
	res=mongo.db.workflow_tasks.find_one({'_id':ObjectId(id)})
	if not res:
		return jsonify(status=400, msg='can not find workflow_task', data=None), 400
	res['_id']=str(res['_id'])
	return jsonify(status=200, msg='success', data=res), 200


@dag.route('/workflow_task/<id>/stop',methods=['POST'])
def stop_workflow_task(id):
	res=mongo.db.workflow_tasks.find_one({'_id':ObjectId(id)},{'state':1})
	if not res or res['state'] != 'running':
		return jsonify(status=400, msg='can not stop', data=None), 400
	mongo.db.workflow_tasks.update({"_id":ObjectId(id)},{"$set":{"isStop":True}})
	return jsonify(status=200, msg='success', data=None), 200

@dag.route('/workflow_task/<id>',methods=['DELETE'])
def delete_workflow_task(id):
	res=mongo.db.workflow_tasks.find_one({'_id':ObjectId(id)},{'_id':1})
	if res:
		mongo.db.workflow_tasks.remove({'_id':ObjectId(id)})	
	return jsonify(status = 200, msg = 'success', data = None), 200



def start_action(taskId,action):
	print("start action:" + taskId + "-" + action['id'])
	operatorName = action['componentId']
	operator = mongo.db.operators.find_one({'operatorName': operatorName})
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


# {
# 	"_id":"",
# 	"isStop":False,
# 	"state":"",
# 	"totalNum":0,
# 	"finishNum":0,
# 	"startTime":"",
# 	"endTime":"",
# 	"actions":{
# 		"id":{
# 			"id":"actionA",
# 			"type":"action",
# 			"paramSetting":"",
# 			"script":"",
# 			"executeTime":"",
# 			"waitNum":0,
# 			"preActions":[],		
#           "nextActions":[],
# 			"state":None,
# 			}
# 	},
# }
def parse(data):
	actions={}
	actionNum=0
	for node in data['nodes']:
		actionNum=actionNum+1
		action={
		"id": node['id'],
		"type": node['type'],
		"componentId": node['componentId'],
		"paramSetting": node.get('paramSetting'),
		"script": node['script'],
		"executeTime": None,
		"waitNum": 0,
		"preActions": [],		
		"nextActions": [],
		"state": None
		}
		actions[node['id']]= action

	for edge in data['edges']:
		source= edge['source']
		target= edge['target']
		actions[source]['nextActions'].append(target)
		actions[target]['preActions'].append(source)
		actions[target]['waitNum']=actions[target]['waitNum']+1
	
	workflow_task= {
		"isStop": False,
		"workflowName": data.get('workflowName'),
		"state": "create",
		"actionNum": actionNum,
		"finishNum": 0,
		"startTime": None,
		"endTime": None,
		"actions":actions
	}	
	# print(workflow_task)
	return workflow_task