ai-ui-controller/
│
├── main.py                    # 主程序入口
├── config.py                  # 配置文件
├── requirements.txt           # 依赖包列表
├── README.md                  # 项目说明
│
├── base/                      # 基类定义
│   ├── __init__.py
│   ├── agent.py               # 代理基类
│   ├── perception.py          # 感知基类
│   ├── executor.py            # 执行器基类
│   ├── brain.py               # 决策基类
│   └── middleware.py          # 中间件基类和管理器
│
├── core/                      # 核心实现
│   ├── __init__.py  
│   ├── ui_agent.py            # 主代理实现
│   ├── screen_capture.py      # 屏幕捕获实现
│   ├── input_controller.py    # 输入控制实现
│   └── llm_decision.py        # 大模型决策实现
│
├── middlewares/               # 中间件实现
│   ├── __init__.py
│   ├── throttling.py          # 操作限流中间件
│   ├── logging_mw.py          # 日志记录中间件
│   └── state_tracking.py      # 状态追踪中间件
│
└── utils/                     # 工具函数
    ├── __init__.py
    └── logger.py              # 日志配置