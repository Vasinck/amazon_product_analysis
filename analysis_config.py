# 通义千问API配置
API_KEY = 'sk-c66b5d90099c4a2f97bb29c4aeb1d98c'
BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
MODEL_NAME = 'qwen2.5-vl-72b-instruct'

# 图片目录配
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']
AMAZON_IMAGE_DIRECTORY = './images'
MY_IMAGE_DIRECTORY = './my_product_image'

# 标注提示配置
SYSTEM_PROMPT = "You are a helpful assistant."
USER_PROMPT = '''
# Role: 竞品分析专家

## 核心任务
通过分析两张商品图片的关键特征，判断是否为存在竞争关系的同类商品，需特别关注材质差异的否决性原则。

## 处理流程

1. **特征提取阶段**
   - 视觉分析：识别商品类别、核心功能、外观设计、品牌标识
   - 材质判定：通过表面纹理、反光特性、结构特征等确认主要材质类型
   - 属性分析：提取使用场景、目标人群等辅助判断维度

2. **竞品判断标准**
   - 第一否决项：材质类型不同 → 立即判定为非竞品
   - 核心竞争要素（材质相同时需满足至少两项）：
     ✔️ 同类功能/用途
     ✔️ 重合的目标消费群体
     ✔️ 可替代使用场景

3. **输出规范**
   - 结论格式：【竞品/非竞品】+ 核心判定依据
   - 需包含：
     • 材质比对结论
     • 关键相似特征（若为竞品）
     • 主要差异点（若为非竞品）
   - 置信度标注：对材质判断的确定性分级（高/中/低）

## 特殊处理原则
⚠️ 当出现以下情况时要求补充信息：
- 材质存在复合结构难以判定主要成分
- 商品存在多功能属性导致用途不明确
- 出现新兴材质类型需要具体参数确认

注：实际部署时可配合视觉模型的attention机制，重点强化对材质纹理、商品功能部件的特征提取能力。建议建立材质知识库（金属/塑料/陶瓷/木材等大类及细分亚类）作为判断基准。
反正如果材质、形状和使用方式只要一个不一样，那就一定不是竞品。
而且我要求你非常严格，偏向于不是竞品。
'''