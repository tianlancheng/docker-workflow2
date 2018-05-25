# -*- coding: utf-8 -*-
from flask import Blueprint,request
from flask import jsonify
from base import require_args,require_json
from app import app,mongo
import datetime
from bson.objectid import ObjectId
import json

operator = Blueprint('operator',__name__)

@operator.route('/operator',methods=['POST'])
@require_json("operatorName")
def add_operator():
	data = json.loads(request.get_data())
	res=mongo.db.operators.find_one({'operatorName':data['operatorName']},{'_id':1})
	if res:
		return jsonify(status=400, msg='operatorName already exists', data=None), 400

	data["cteateTime"]=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
	id=mongo.db.operators.insert(data)
	res=mongo.db.operators.find_one({'_id':id})
	res['_id']=str(res['_id'])
	return jsonify(status=200, msg='success', data=res), 200

@operator.route('/operator/<id>',methods=['GET'])
def get_operator(id):
	res=mongo.db.operators.find_one({'_id':ObjectId(id)})
	if not res:
		return jsonify(status=400, msg='can not find operator', data=None), 400
	res['_id']=str(res['_id'])
	return jsonify(status=200, msg='success', data=res), 200

@operator.route('/operators',methods=['GET'])
@require_args('currentPage','pageSize')
def get_operators():
	currentPage=int(request.args.get("currentPage"))
	pageSize=int(request.args.get("pageSize"))
	skip=(currentPage-1)*pageSize
	filters=request.args.get('filters')
	if not filters:
		filters={}
	else:
		filters=json.loads(filters)
	results=mongo.db.operators.find(filters).sort("cteateTime",-1).skip(skip).limit(pageSize)
	data=[]
	for result in results:
		result['_id']=str(result['_id'])
		data.append(result)  
	return jsonify(status=200, msg='success', data=data), 200

@operator.route('/operator/<id>',methods=['PUT'])
@require_json("operatorName")
def update_operator(id):
	data = json.loads(request.get_data())
	res=mongo.db.operators.find_one({'_id':ObjectId(id)},{'_id':1})
	if not res:
		return jsonify(status=400, msg='can not find operator', data=None), 400

	update_data={}
	if data.get('author'):
		update_data['author'] = data.get('author')
	if data.get('description'):
		update_data['description'] = data.get('description')
	if data.get('parameters'):
		update_data['parameters'] = data.get('parameters')
	mongo.db.operators.update({"_id":ObjectId(id)},{"$set":update_data})
	res=mongo.db.operators.find_one({'_id':ObjectId(id)})
	res['_id']=str(res['_id'])
	return jsonify(status=200, msg='success', data=res), 200

@operator.route('/operator/<id>',methods=['DELETE'])
def delete_operator(id):
	res=mongo.db.operators.find_one({'_id':ObjectId(id)},{'_id':1})
	if not res:
		return jsonify(status=400, msg='can not find operator', data=None), 400
	mongo.db.operators.remove({'_id':ObjectId(id)})
	return jsonify(status=200, msg='success', data=None), 200