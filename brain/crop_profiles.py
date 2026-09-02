"""作物与营养液目标配置。

EC 统一使用 μS/cm。稀释比例仅作为厂家标签记录，不直接换算为泵运行时间。
"""



CROP_PROFILES = {
    "lettuce": {
        "crop_name": "生菜",
        "nutrient_product": "通用叶菜营养液",
        "ec_targets": {
            "seedling": {"label": "育苗期", "min": 600.0, "max": 1000.0, "dilution": None},
            "growth": {"label": "生长期", "min": 1000.0, "max": 1500.0, "dilution": None},
            "mature": {"label": "成熟期", "min": 1300.0, "max": 1800.0, "dilution": None},
        },
    },
    "tomato_fruit_ab": {
        "crop_name": "番茄",
        "nutrient_product": "瓜果专用营养液 A+B",
        "source": "用户提供的产品标签",
        "ec_targets": {
            "seedling": {
                "label": "育苗期（三四片真叶）",
                "min": 600.0,
                "max": 1000.0,
                "dilution": "1:1000",
            },
            "growth": {
                "label": "生长期（移植到设备）",
                "min": 1000.0,
                "max": 1500.0,
                "dilution": "1:500",
            },
            "mature": {
                "label": "成熟期（开花到结果）",
                "min": 1400.0,
                "max": 1900.0,
                "dilution": "1:300",
            },
        },
    },
}


def get_crop_profile(profile_name: str) -> dict:
    """返回指定作物配置。"""
    try:
        return CROP_PROFILES[profile_name]
    except KeyError as exc:
        available = ", ".join(sorted(CROP_PROFILES))
        raise ValueError(f"未知 CROP_PROFILE={profile_name!r}，可选值: {available}") from exc


def get_growth_stage(profile: dict, stage_name: str) -> dict:
    """返回指定阶段配置，不允许 AI 靠图片自行改变阶段。"""
    try:
        return profile["ec_targets"][stage_name]
    except KeyError as exc:
        available = ", ".join(sorted(profile["ec_targets"]))
        raise ValueError(f"未知 GROWTH_STAGE={stage_name!r}，可选值: {available}") from exc
