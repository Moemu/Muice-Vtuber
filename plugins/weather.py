from plugin.func_call import on_function_call
from plugin.func_call.parameter import String
from config import Config
import httpx
import logging

plugin_config = Config()
logger = logging.getLogger("Muice.Plugin.weather")

@on_function_call(description="可以用于查询天气").params(
    location = String(description="城市。(格式:城市英文名,国家两位大写英文简称)", required=True)
)
async def get_weather(location: str) -> str:
    """查询指定地点的天气信息"""
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    # 构建请求参数
    params = {
        "q": location,
        "appid": plugin_config.WEATHER,
        "units": "metric",  # 摄氏温度
        "lang": "zh_cn"     # 中文
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"请求失败: {response.status_code} - {response.text}")
                return f"获取天气信息失败：{response.status_code}"

            data = response.json()

            # 解析返回的天气数据
            city = data.get("name", location)
            weather_desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            # 格式化天气信息
            result = (
                f"{city} 的天气：\n"
                f"天气：{weather_desc}\n"
                f"温度：{temp}°C\n"
                f"湿度：{humidity}%\n"
                f"风速：{wind_speed} m/s"
            )
            return result

    except httpx.HTTPError as e:
        logger.error(f"HTTP请求异常: {str(e)}")
        return "获取天气信息失败，请稍后再试。"
    except Exception as e:
        logger.error(f"出现异常: {str(e)}")
        return "查询天气时发生错误，请检查日志。"