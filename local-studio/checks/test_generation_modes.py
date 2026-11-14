"""Input provenance, restored branches, seed validation, and old-project compatibility."""
import importlib.util
import io
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image

spec=importlib.util.spec_from_file_location('studio',Path(__file__).parents[1]/'server.py')
studio=importlib.util.module_from_spec(spec);spec.loader.exec_module(studio)

class GenerationModes(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old_data=studio.DATA
  studio.DATA=Path(self.tmp.name);studio.GPU=threading.Lock();studio.JOBS={}
  raw=io.BytesIO();Image.new('RGB',(128,128),'gray').save(raw,format='PNG')
  self.p=studio.create_project(raw.getvalue(),'mode test');self.calls=[]
 def tearDown(self):
  studio.DATA=self.old_data;self.tmp.cleanup()
 def fake_generate(self,cmd,**kwargs):
  source=Path(cmd[cmd.index('--image-paths')+1]);target=Path(cmd[cmd.index('--output')+1])
  self.calls.append({'input':source.read_bytes(),'seed':cmd[cmd.index('--seed')+1]})
  Image.new('RGB',(128,128),(20*len(self.calls),40,60)).save(target)
  return SimpleNamespace(returncode=0)
 def generate(self,mode=None,seed=42):
  p=studio.read(self.p['id'])
  with patch.object(studio.subprocess,'run',side_effect=self.fake_generate):
   j=studio.start_job(p['id'],p['revision'],'image',options=None if mode is None else studio.generation_options(mode,seed))
   deadline=time.monotonic()+5
   while studio.GPU.locked() and time.monotonic()<deadline:time.sleep(.01)
  self.assertFalse(studio.GPU.locked());self.assertEqual(j['status'],'done',j)
  return studio.read(p['id'])['versions'][-1]
 def test_old_project_defaults_to_original(self):
  v=self.generate();self.assertEqual(v['mode'],'regenerate');self.assertIsNone(v['input_version'])
  self.assertEqual(self.calls[-1]['input'],(studio.folder(self.p['id'])/'reference.png').read_bytes())
 def test_first_sequential_uses_original_then_previous_output(self):
  a=self.generate('sequential');b=self.generate('sequential')
  self.assertIsNone(a['input_version']);self.assertEqual(b['input_version'],a['id'])
  self.assertEqual(b['input_sha256'],a['output_sha256']);self.assertEqual(self.calls[-1]['seed'],'42')
 def test_regeneration_ignores_current_output(self):
  a=self.generate('sequential');b=self.generate('regenerate')
  self.assertIsNone(b['input_version']);self.assertEqual(b['parent'],a['id'])
  self.assertEqual(self.calls[-1]['input'],(studio.folder(self.p['id'])/'reference.png').read_bytes())
 def test_restored_branch_is_sequential_source(self):
  a=self.generate('sequential');self.generate('sequential')
  p=studio.read(self.p['id']);studio.change(p['id'],p['revision'],lambda d:d.update(current_version=a['id']))
  b=self.generate('sequential',314);self.assertEqual(b['input_version'],a['id']);self.assertEqual(b['input_sha256'],a['output_sha256'])
 def test_invalid_seed_or_mode(self):
  for mode,seed in [('bad',42),([],42),('sequential',True),('regenerate',-1),('regenerate',1.5),('regenerate',2147483648)]:
   with self.assertRaises(ValueError):studio.generation_options(mode,seed)
 def test_missing_input_releases_gpu_without_locking_project(self):
  (studio.folder(self.p['id'])/'reference.png').unlink()
  with self.assertRaises(ValueError):studio.start_job(self.p['id'],0,'image')
  self.assertFalse(studio.GPU.locked());self.assertIsNone(studio.read(self.p['id'])['active_job'])

 def test_chat_completion_persists_state_and_job_outcome(self):
  updated=dict(self.p['state'],shirt_color='navy')
  cases=[
   ({'state':updated,'message':'적용 완료'},'done',updated,'적용 완료',True),
   ({'clarification':'확인'*150},'needs_input',None,'확인'*100,False),
  ]
  for response,status,state,message,applied in cases:
   with self.subTest(status=status):
    project=studio.read(self.p['id'])
    if state is None:
     state=project['state']
    # Start the worker synchronously so completion checks need no polling.
    with patch.object(studio.threading,'Thread'):
     job=studio.start_job(project['id'],project['revision'],'chat','셔츠를 바꿔줘')
    pending=studio.read(project['id'])
    process=SimpleNamespace(returncode=0,stdout=json.dumps(response),stderr='')
    with patch.object(studio.subprocess,'run',return_value=process):
     studio.worker(job,pending,'셔츠를 바꿔줘')
    saved=studio.read(project['id'])
    self.assertEqual(saved['state'],state)
    self.assertEqual(saved['revision'],project['revision']+2)
    self.assertIsNone(saved['active_job'])
    self.assertEqual(len(saved['messages']),len(project['messages'])+1)
    self.assertEqual(saved['messages'][-1],dict(
     request='셔츠를 바꿔줘',state=state,reply=message,applied=applied,
     created=saved['messages'][-1]['created']))
    self.assertEqual(job['status'],status)
    self.assertEqual(job['message'],message)
    self.assertEqual(json.loads((studio.folder(project['id'])/job['id']/'job.json').read_text()),job)
    self.assertFalse(studio.GPU.locked())

 def test_chat_failure_preserves_state_and_history(self):
  for response in [SimpleNamespace(returncode=1,stdout='',stderr='failed'),
                   SimpleNamespace(returncode=0,stdout='{"state": {}}',stderr='')]:
   with self.subTest(response=response):
    project=studio.read(self.p['id'])
    with patch.object(studio.threading,'Thread'):
     job=studio.start_job(project['id'],project['revision'],'chat','셔츠를 바꿔줘')
    with patch.object(studio.subprocess,'run',return_value=response):
     studio.worker(job,studio.read(project['id']),'셔츠를 바꿔줘')
    saved=studio.read(project['id'])
    self.assertEqual(saved['state'],project['state'])
    self.assertEqual(saved['messages'],project['messages'])
    self.assertEqual(saved['revision'],project['revision']+2)
    self.assertIsNone(saved['active_job'])
    self.assertEqual(job['status'],'error')
    self.assertFalse(studio.GPU.locked())

if __name__=='__main__':unittest.main()
