"""离线回归：不连接传感器、继电器或外部 API。"""
import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'brain'))
from vision import GrowthObservation, load_stage, update_stage, save_stage
from crop_profiles import CROP_PROFILES


class VisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'growth.json'
        self.targets = CROP_PROFILES['tomato_fruit_ab']['ec_targets']
        self.initial = load_stage(self.path, 'batch', 'tomato_fruit_ab', 'seedling', self.targets)

    def obs(self, stage='growth', usable=True):
        return GrowthObservation(image_usable=usable, stage=stage, evidence=['多片展开真叶'], condition='叶片舒展')

    def test_confirmation_requires_two_distinct_valid_images(self):
        first = update_stage(self.initial, self.obs(), 'photo1')
        self.assertEqual(first['effective_stage'], 'seedling')
        duplicate = update_stage(first, self.obs(), 'photo1')
        self.assertEqual(duplicate['count'], 1)
        second = update_stage(first, self.obs(), 'photo2')
        self.assertEqual(second['effective_stage'], 'growth')
        save_stage(self.path, second)
        self.assertEqual(load_stage(self.path, 'batch', 'tomato_fruit_ab', 'seedling', self.targets)['effective_stage'], 'growth')
        self.assertEqual(load_stage(self.path, 'new-batch', 'tomato_fruit_ab', 'seedling', self.targets)['effective_stage'], 'seedling')

    def test_missing_image_breaks_streak_and_manual_override(self):
        first = update_stage(self.initial, self.obs(), 'photo1')
        missing = update_stage(first, None, None)
        self.assertEqual(update_stage(missing, self.obs(), 'photo2')['effective_stage'], 'seedling')
        self.assertEqual(update_stage(first, self.obs(), 'photo2', 'manual')['effective_stage'], 'seedling')
        self.assertEqual(update_stage(first, self.obs(usable=False), 'photo2')['count'], 0)

    def test_flowering_and_fruiting_map_to_existing_target(self):
        first = update_stage(self.initial, self.obs('flowering'), 'photo1')
        second = update_stage(first, self.obs('fruiting'), 'photo2')
        self.assertEqual(second['effective_stage'], 'mature')
        self.assertEqual(self.targets['mature']['min'], 1400)

    def test_api_carries_image_and_execution_uses_confirmed_stage(self):
        config = types.ModuleType('config')
        values = dict(THOUGHT_LOG_PATH=Path(self.tmp.name)/'thought.log', SNAPSHOT_DIR=Path(self.tmp.name),
            LIGHT_ON_HOUR=6, LIGHT_OFF_HOUR=22, DASHSCOPE_API_KEY='test', DASHSCOPE_BASE_URL='https://unused',
            QWEN_MODEL='test', CROP_NAME='番茄', CROP_PROFILE_NAME='tomato_fruit_ab', GROWTH_STAGE='seedling',
            NUTRIENT_PRODUCT='A+B', EC_TARGETS=self.targets, CURRENT_GROWTH_STAGE=self.targets['seedling'],
            EC_TARGET_MIN=600, EC_TARGET_MAX=1000, NUTRIENT_DOSING_ENABLED=True, CONTROL_ENABLED=True,
            RUN_MODE='control', DATA_DIR=Path(self.tmp.name), PLANTING_BATCH='batch', PLANTING_START_DATE='2026-08-12',
            GROWTH_STAGE_MODE='auto', GROWTH_STATE_PATH=self.path)
        config.__dict__.update(values)
        sensor = types.ModuleType('sensor_logger')
        sensor.read_sensors = lambda: {}
        sensor.get_latest = lambda n: []
        commands = []
        class Bridge:
            def send_command(self, cmd):
                commands.append(cmd)
                return {'status': 'ok', 'id': cmd['id']}
        serial = types.ModuleType('serial_bridge')
        serial.SerialBridge = Bridge
        api = types.ModuleType('openai')
        payloads = []
        def create(**kwargs):
            payloads.append(kwargs)
            result = dict(growth=self.obs().model_dump(), thought='观察到真叶',
                          actions=[dict(relay_id=1, state=1, duration_seconds=2)])
            return types.SimpleNamespace(id='request-test', choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=json.dumps(result)))])
        api.OpenAI = lambda **kw: types.SimpleNamespace(close=lambda: None, chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
        api.DefaultHttpxClient = lambda **kw: None
        with patch.dict(sys.modules, {'config': config, 'sensor_logger': sensor, 'serial_bridge': serial, 'openai': api}):
            sys.modules.pop('ai_engine', None)
            engine = importlib.import_module('ai_engine')
            state = dict(sensor_data={'ec': 800}, history=[], image_path='current.jpg', hardware_status={})
            block = {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,TEST'}}
            with patch.object(engine, 'prepare_image', return_value=(block, {'sha256': 'photo1', 'prepared': True})), patch('time.sleep'):
                engine.decide_node(state)
                engine.execute_node(state)
                self.assertEqual(payloads[-1]['messages'][-1]['content'][1], block)
                self.assertTrue(state['results'][0]['blocked'])
                self.assertEqual(commands, [])
            with patch.object(engine, 'prepare_image', return_value=(block, {'sha256': 'photo2', 'prepared': True})), patch('time.sleep'):
                engine.decide_node(state)
                engine.execute_node(state)
                self.assertEqual(state['effective_stage'], 'growth')
                self.assertEqual(commands[-1]['duration'], 10)
            state['sensor_data']['ec'] = 1000
            engine.execute_node(state)
            self.assertTrue(state['results'][0]['blocked'])
            with patch.object(engine, 'prepare_image', side_effect=ValueError('照片过期')):
                engine.decide_node(state)
                self.assertEqual(len(payloads[-1]['messages'][-1]['content']), 1)
                self.assertFalse(state['growth']['image_usable'])
                self.assertEqual(state['effective_stage'], 'growth')
            with patch.object(api, 'OpenAI', side_effect=RuntimeError('API unavailable')):
                engine.decide_node(state)
                self.assertEqual(state['actions'], [])
                self.assertEqual(state['model_used'], 'None')
                self.assertEqual(json.loads(self.path.read_text())['count'], 0)
            state['actions'] = [dict(relay_id=1, state=1, duration_seconds=10)]
            with patch.object(engine, 'CONTROL_ENABLED', False), patch.object(engine, 'SerialBridge', side_effect=AssertionError('不应访问硬件')):
                engine.execute_node(state)
                self.assertTrue(state['results'][0]['blocked'])
        sys.modules.pop('ai_engine', None)

    def test_00_real_image_encoding_and_staleness(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest('需要生产环境已安装的 OpenCV')
        import os
        import time
        import base64
        from vision import prepare_image
        path = Path(self.tmp.name) / 'sample.jpg'
        cv2.imwrite(str(path), np.full((1500, 2000, 3), 120, dtype=np.uint8))
        block, metadata = prepare_image(path)
        raw = base64.b64decode(block['image_url']['url'].split(',')[1])
        decoded = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(max(decoded.shape[:2]), 1280)
        self.assertEqual(metadata['bytes'], len(raw))
        os.utime(path, (time.time()-600, time.time()-600))
        with self.assertRaises(ValueError):
            prepare_image(path)
        with self.assertRaises(ValueError):
            prepare_image(None)


if __name__ == '__main__':
    unittest.main()
