"""图片输入与按种植批次保存的生长阶段；不访问硬件。"""
import base64
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field
from typing import Literal


class GrowthObservation(BaseModel):
    image_usable: bool
    stage: Literal['seedling', 'growth', 'flowering', 'fruiting', 'mature', 'unknown']
    evidence: list[str]
    condition: str
    uncertainty: list[str] = Field(default_factory=list)


def prepare_image(image_path, max_age=300):
    """只接受本轮新鲜图片，缩放后返回 API 图片块和可审计元数据。"""
    import cv2

    if not image_path:
        raise ValueError('本轮拍照失败或未拍照')
    path = Path(image_path)
    age = time.time() - path.stat().st_mtime
    if not 0 <= age <= max_age:
        raise ValueError(f'照片过期或时间异常：{age:.0f} 秒')
    frame = cv2.imread(str(path))
    if frame is None:
        raise ValueError('照片无法解码')
    height, width = frame.shape[:2]
    scale = min(1.0, 1280 / max(height, width))
    if scale < 1:
        frame = cv2.resize(frame, (round(width * scale), round(height * scale)))
    ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError('照片编码失败')
    data = encoded.tobytes()
    metadata = {
        'path': str(path),
        'captured_at': datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds'),
        'sha256': hashlib.sha256(data).hexdigest(),
        'bytes': len(data), 'prepared': True, 'request_succeeded': False,
    }
    return {'type': 'image_url', 'image_url': {
        'url': 'data:image/jpeg;base64,' + base64.b64encode(data).decode('ascii')
    }}, metadata


def load_stage(path, batch, profile, fallback, targets):
    default = {'batch': batch, 'profile': profile, 'effective_stage': fallback,
               'candidate': None, 'count': 0, 'last_image': None}
    try:
        saved = json.loads(Path(path).read_text(encoding='utf-8'))
        if (saved.get('batch') == batch and saved.get('profile') == profile
                and saved.get('effective_stage') in targets):
            return {**default, **saved}
    except (OSError, ValueError, AttributeError):
        pass
    return default


def update_stage(previous, observation, image_id, mode='auto', fallback='seedling'):
    result = dict(previous)
    if mode == 'manual':
        result.update(effective_stage=fallback, candidate=None, count=0, last_image=None)
        return result
    if (not image_id or not observation or not observation.image_usable
            or observation.stage == 'unknown'
            or not any(item.strip() for item in observation.evidence)):
        result.update(candidate=None, count=0)
        return result
    if image_id == result.get('last_image'):
        return result
    stage = {'flowering': 'mature', 'fruiting': 'mature'}.get(observation.stage, observation.stage)
    count = result.get('count', 0) + 1 if result.get('candidate') == stage else 1
    result.update(candidate=stage, count=min(count, 2), last_image=image_id)
    if stage == result['effective_stage'] or count >= 2:
        result['effective_stage'] = stage
    return result


def save_stage(path, stage):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(stage, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)
