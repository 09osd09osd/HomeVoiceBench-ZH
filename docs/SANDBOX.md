# 完整工具沙箱

每题独立内存状态，不连接真实家电。4个房间、11个设备、20条传感器读数、4个虚构媒体条目。可信身份由执行器注入；模型不能通过参数冒充身份。逻辑时钟每工具推进100毫秒，每用户轮推进1秒。

单次device_set的多字段写入原子检查。权限、数值范围、离线、延迟及错误读数由固定夹具控制。ok=true不等于执行完成，pending只是接受；取消已经提交的任务不回滚。request_id支持传输重试幂等，不把真实重复创建当网络重试。

| 工具 | 作用 | 权限 | 状态影响 |
|---|---|---|---|
| home_get | 读取当前用户可见的家庭公共设置。 | home/read；不可见房间和偏好不返回。 | 只读。 |
| device_list | 按房间和类型查找设备及其能力。 | 只列出当前用户可见设备。 | 只读。 |
| clock_get | 读取场景时间。 | 所有已认证用户可读。 | 只读。 |
| policy_get | 检查当前用户对指定资源的动作权限。 | 检查者固定为可信 actor，不接受模型传入身份。 | 只读。 |
| device_get | 读取指定设备当前状态。 | device_get 权限。 | 只读。 |
| device_set | 修改指定设备状态。 | device_set 权限；必须逐字段符合设备能力。 | 同步成功提交状态；延迟时创建 pending 任务。 |
| sensor_read | 读取房间内指定环境指标。 | sensor_read 权限。 | 只读。 |
| schedule_list | 查询当前用户可见的未来安排。 | schedule_list；按 owner 和权限过滤。 | 只读。 |
| schedule_create | 新建提醒、闹钟或定时设备动作。 | schedule_create；定时设备动作在创建和触发时均复核权限。 | 建立 active 安排，owner 从可信 actor 注入。 |
| schedule_update | 修改已有安排，保留安排 ID 和归属。 | schedule_update 且资源归属/授权匹配。 | 原子替换指定顶层字段。 |
| schedule_cancel | 取消未来安排。 | schedule_cancel 权限。 | 将 active 改为 cancelled；已取消返回成功且不重复产生副作用。 |
| media_search | 搜索固定媒体库。 | media_search 权限。 | 只读。 |
| media_play | 在指定设备播放媒体。 | media_play 及目标设备权限。 | 停止该设备已有播放会话，新建 playing 会话。 |
| media_control | 控制现有播放会话。 | media_control 且归属/授权匹配。 | 更新播放状态或进度。 |
| task_get | 读取异步执行任务状态。 | task_get 且归属/授权匹配。 | 只读；先处理逻辑时钟已到期事件。 |
| task_cancel | 取消仍可取消的异步任务。 | task_cancel 且归属/授权匹配。 | pending 或标为 cancellable 的 running 可取消。 |


## home_get

读取当前用户可见的家庭公共设置。

- 不返回完整私有夹具、答案、未授权用户资料。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {},
    "required": [],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "家庭公共设置。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/HomeInfo",
            "description": "家庭公共设置。"
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## device_list

按房间和类型查找设备及其能力。

- 省略筛选表示全部可见设备；结果按 ID 排序。
- 实时开关与在线状态通过 device_get 获取。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "room_id": {
        "type": "string",
        "description": "按房间过滤。"
      },
      "device_type": {
        "type": "string",
        "description": "设备类型。",
        "enum": [
          "light",
          "air_conditioner",
          "curtain",
          "fan",
          "purifier",
          "tv",
          "speaker",
          "vacuum"
        ]
      }
    },
    "required": [],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "设备目录。",
        "anyOf": [
          {
            "type": "object",
            "description": "设备目录。",
            "properties": {
              "devices": {
                "type": "array",
                "description": "可见设备列表。",
                "items": {
                  "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/DeviceInfo",
                  "description": "设备目录。"
                },
                "minItems": 0
              }
            },
            "required": [
              "devices"
            ],
            "additionalProperties": false
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## clock_get

读取场景时间。

- 使用逻辑时钟，不使用执行机器的当前日期。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {},
    "required": [],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "场景时间。",
        "anyOf": [
          {
            "type": "object",
            "description": "场景时间。",
            "properties": {
              "now": {
                "type": "string",
                "format": "date-time",
                "description": "当前时间。"
              },
              "timezone": {
                "type": "string",
                "description": "IANA 时区。"
              }
            },
            "required": [
              "now",
              "timezone"
            ],
            "additionalProperties": false
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## policy_get

检查当前用户对指定资源的动作权限。

- 拒绝优先、未匹配默认拒绝。
- 权限不足不泄露资源私有内容。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "resource_type": {
        "type": "string",
        "description": "资源类型。",
        "enum": [
          "home",
          "device",
          "sensor",
          "schedule",
          "media",
          "playback",
          "task"
        ]
      },
      "resource_id": {
        "type": "string",
        "description": "目标资源；新建自身安排时使用 self。"
      },
      "action": {
        "type": "string",
        "description": "工具名。"
      }
    },
    "required": [
      "resource_type",
      "resource_id",
      "action"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "权限结论。",
        "anyOf": [
          {
            "type": "object",
            "description": "权限结论。",
            "properties": {
              "allowed": {
                "type": "boolean",
                "description": "是否允许。"
              },
              "reason": {
                "type": "string",
                "description": "可公开的依据。"
              }
            },
            "required": [
              "allowed",
              "reason"
            ],
            "additionalProperties": false
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## device_get

读取指定设备当前状态。

- 设备离线返回 DEVICE_OFFLINE，不把缓存状态冒充新状态。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "device_id": {
        "type": "string",
        "description": "目录中的设备 ID。"
      }
    },
    "required": [
      "device_id"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "设备当前记录。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Device",
            "description": "设备当前记录。"
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## device_set

修改指定设备状态。

- 单次对一台设备的修改原子提交，任一字段错误则整次不修改。
- 不同设备的调用分别提交，允许出现部分成功。
- pending/running 不能声称已经成功；committed 后无法通过 task_cancel 回滚。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "device_id": {
        "type": "string",
        "description": "目标设备。"
      },
      "changes": {
        "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/DeviceChanges",
        "description": "修改字段。"
      }
    },
    "required": [
      "device_id",
      "changes"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "pending",
          "running",
          "failed"
        ]
      },
      "data": {
        "description": "",
        "anyOf": [
          {
            "anyOf": [
              {
                "type": "object",
                "description": "同步成功。",
                "properties": {
                  "device": {
                    "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Device",
                    "description": "修改后的设备。"
                  }
                },
                "required": [
                  "device"
                ],
                "additionalProperties": false
              },
              {
                "type": "object",
                "description": "异步已接受。",
                "properties": {
                  "task": {
                    "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Task",
                    "description": "尚在执行的任务。"
                  }
                },
                "required": [
                  "task"
                ],
                "additionalProperties": false
              }
            ]
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "description": "异步任务 ID；同步/查询通常为 null。",
        "anyOf": [
          {
            "type": "string",
            "description": "异步任务 ID；同步/查询通常为 null。"
          },
          {
            "type": "null"
          }
        ]
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "status": {
              "enum": [
                "pending",
                "running"
              ]
            }
          }
        },
        "then": {
          "properties": {
            "operation_id": {
              "type": "string"
            },
            "data": {
              "type": "object",
              "required": [
                "task"
              ],
              "properties": {
                "task": {
                  "properties": {
                    "status": {
                      "enum": [
                        "pending",
                        "running"
                      ]
                    }
                  }
                }
              },
              "additionalProperties": false
            }
          }
        }
      }
    ]
  }
}
```

## sensor_read

读取房间内指定环境指标。

- 不存在或离线的指定指标返回明确错误，不生成估计值。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "room_id": {
        "type": "string",
        "description": "目标房间。"
      },
      "metrics": {
        "type": "array",
        "description": "需要的指标。",
        "items": {
          "type": "string",
          "description": "测量类型。",
          "enum": [
            "temperature_c",
            "humidity_pct",
            "illuminance_lux",
            "co2_ppm",
            "presence"
          ]
        },
        "minItems": 1
      }
    },
    "required": [
      "room_id",
      "metrics"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "环境读数。",
        "anyOf": [
          {
            "type": "object",
            "description": "环境读数。",
            "properties": {
              "readings": {
                "type": "array",
                "description": "带时间的读数。",
                "items": {
                  "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Sensor",
                  "description": "观测。"
                },
                "minItems": 0
              }
            },
            "required": [
              "readings"
            ],
            "additionalProperties": false
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## schedule_list

查询当前用户可见的未来安排。

- from/to 都省略表示不限制时间；只提供一个边界则另一边无界。
- 重复安排按区间内是否存在一次触发匹配；返回安排本身，不重复展开。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "status": {
        "type": "string",
        "description": "筛选状态，省略默认 active。",
        "enum": [
          "active",
          "cancelled",
          "all",
          "completed"
        ]
      },
      "kind": {
        "type": "string",
        "description": "安排类型。",
        "enum": [
          "reminder",
          "alarm",
          "device_action"
        ]
      },
      "from": {
        "type": "string",
        "format": "date-time",
        "description": "查询区间起点，含。"
      },
      "to": {
        "type": "string",
        "format": "date-time",
        "description": "查询区间终点，不含。"
      }
    },
    "required": [],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "安排列表。",
        "anyOf": [
          {
            "type": "object",
            "description": "安排列表。",
            "properties": {
              "schedules": {
                "type": "array",
                "description": "按下次触发时间、ID 排序的结果。",
                "items": {
                  "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Schedule",
                  "description": "安排。"
                },
                "minItems": 0
              }
            },
            "required": [
              "schedules"
            ],
            "additionalProperties": false
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## schedule_create

新建提醒、闹钟或定时设备动作。

- reminder：message 必须非空，target_device_id=null，actions=[]。
- alarm：message 非空，target_device_id 必须是可播放设备，actions=[]。
- device_action：message=null、target_device_id=null、actions 非空。
- 过去的一次性时间返回 INVALID_TIME；设备动作按 actions 顺序执行，失败后停止剩余动作，记录已完成部分。
- 一次性安排到期派发后标为completed；周期安排保持active并更新last_triggered_at。设备动作或闹钟失败另保留任务/播放错误，不能伪造成功。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "kind": {
        "type": "string",
        "description": "安排类型。",
        "enum": [
          "reminder",
          "alarm",
          "device_action"
        ]
      },
      "when": {
        "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/When",
        "description": "触发时间。"
      },
      "payload": {
        "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Payload",
        "description": "安排内容。"
      }
    },
    "required": [
      "kind",
      "when",
      "payload"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "kind": {
              "const": "reminder"
            }
          }
        },
        "then": {
          "properties": {
            "payload": {
              "properties": {
                "message": {
                  "type": "string",
                  "minLength": 1
                },
                "target_device_id": {
                  "type": "null"
                },
                "actions": {
                  "maxItems": 0
                }
              }
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "kind": {
              "const": "alarm"
            }
          }
        },
        "then": {
          "properties": {
            "payload": {
              "properties": {
                "message": {
                  "type": "string",
                  "minLength": 1
                },
                "target_device_id": {
                  "type": "string"
                },
                "actions": {
                  "maxItems": 0
                }
              }
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "kind": {
              "const": "device_action"
            }
          }
        },
        "then": {
          "properties": {
            "payload": {
              "properties": {
                "message": {
                  "type": "null"
                },
                "target_device_id": {
                  "type": "null"
                },
                "actions": {
                  "minItems": 1
                }
              }
            }
          }
        }
      }
    ]
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "新建安排。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Schedule",
            "description": "新建安排。"
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## schedule_update

修改已有安排，保留安排 ID 和归属。

- patch 至少一项；when/payload 各自完整替换，不做隐含深合并。
- 已取消安排不能恢复；取消后重建需 schedule_create。
- 修改后重新校验类型、时间、设备能力及权限。
- 已完成的一次性安排也不允许修改；需要新建。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "schedule_id": {
        "type": "string",
        "description": "已有安排 ID。"
      },
      "patch": {
        "type": "object",
        "description": "至少提供一项；不允许改变 kind、owner 或 ID。",
        "properties": {
          "when": {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/When",
            "description": "完整替换触发时间。"
          },
          "payload": {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Payload",
            "description": "完整替换安排内容。"
          }
        },
        "required": [],
        "additionalProperties": false,
        "minProperties": 1
      }
    },
    "required": [
      "schedule_id",
      "patch"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "修改后的安排。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Schedule",
            "description": "修改后的安排。"
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## schedule_cancel

取消未来安排。

- 不撤回已经触发的通知，不回滚已经执行的设备动作。
- 已派发的异步任务需分别调用 task_cancel。
- completed安排返回NOT_CANCELLABLE；已触发的执行结果从对应任务记录查询。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "schedule_id": {
        "type": "string",
        "description": "安排 ID。"
      }
    },
    "required": [
      "schedule_id"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "取消后的安排。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Schedule",
            "description": "取消后的安排。"
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## media_search

搜索固定媒体库。

- 对 query 去除首尾空白后按标题子串匹配，结果按 ID 排序；不接实时互联网。
- 空 query 返回 INVALID_ARGUMENT。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "query": {
        "type": "string",
        "description": "搜索词。"
      },
      "media_type": {
        "type": "string",
        "description": "媒体类型。",
        "enum": [
          "music",
          "story",
          "podcast"
        ]
      }
    },
    "required": [
      "query"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "媒体结果。",
        "anyOf": [
          {
            "type": "object",
            "description": "媒体结果。",
            "properties": {
              "items": {
                "type": "array",
                "description": "确定性的搜索结果。",
                "items": {
                  "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Media",
                  "description": "条目。"
                },
                "minItems": 0
              }
            },
            "required": [
              "items"
            ],
            "additionalProperties": false
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## media_play

在指定设备播放媒体。

- 必须是已登记且设备支持的内容。
- 元数据模拟与真实音频播放是不同运行模式；此版状态沙箱不用于测音质和播放延迟。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "content_id": {
        "type": "string",
        "description": "搜索返回的媒体 ID。"
      },
      "device_id": {
        "type": "string",
        "description": "可播放设备 ID。"
      }
    },
    "required": [
      "content_id",
      "device_id"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "新播放会话。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Playback",
            "description": "新播放会话。"
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## media_control

控制现有播放会话。

- seek 必须提供 position_s 且不超过媒体长度；其他动作不得提供该字段。
- 音量通过 device_set 调整；对不适用的状态转换返回 CONFLICT。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "playback_id": {
        "type": "string",
        "description": "播放会话 ID。"
      },
      "action": {
        "type": "string",
        "description": "动作。",
        "enum": [
          "pause",
          "resume",
          "stop",
          "seek"
        ]
      },
      "position_s": {
        "type": "number",
        "description": "seek 的目标秒数。",
        "minimum": 0
      }
    },
    "required": [
      "playback_id",
      "action"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "action": {
              "const": "seek"
            }
          }
        },
        "then": {
          "required": [
            "position_s"
          ]
        },
        "else": {
          "not": {
            "required": [
              "position_s"
            ]
          }
        }
      }
    ]
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "操作后的播放会话。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Playback",
            "description": "操作后的播放会话。"
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## task_get

读取异步执行任务状态。

- 查询成功不等于底层任务成功，必须读取 data.status。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "task_id": {
        "type": "string",
        "description": "执行任务 ID。"
      }
    },
    "required": [
      "task_id"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "任务状态。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Task",
            "description": "任务状态。"
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```

## task_cancel

取消仍可取消的异步任务。

- committed/failed 或不可取消的 running 返回 NOT_CANCELLABLE，状态不回滚。
- 已经 cancelled 的任务返回成功且无新副作用。

完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。

```json
{
  "input_schema": {
    "type": "object",
    "description": "工具参数。",
    "properties": {
      "task_id": {
        "type": "string",
        "description": "执行任务 ID。"
      }
    },
    "required": [
      "task_id"
    ],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "description": "统一工具响应。",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "执行器分配的请求 ID；传输重试沿用。"
      },
      "ok": {
        "type": "boolean",
        "description": "请求是否被接受；true 不一定已经完成。"
      },
      "status": {
        "type": "string",
        "description": "请求执行状态。",
        "enum": [
          "succeeded",
          "failed"
        ]
      },
      "data": {
        "description": "取消后的任务。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Task",
            "description": "取消后的任务。"
          },
          {
            "type": "null"
          }
        ]
      },
      "error": {
        "description": "失败原因。",
        "anyOf": [
          {
            "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
            "description": "失败原因。"
          },
          {
            "type": "null"
          }
        ]
      },
      "operation_id": {
        "type": "null",
        "description": "本工具同步返回，无异步操作ID；task_get的任务ID位于data.id。"
      },
      "clock_time": {
        "type": "string",
        "format": "date-time",
        "description": "本次响应时的场景时钟。"
      }
    },
    "required": [
      "request_id",
      "ok",
      "status",
      "data",
      "error",
      "operation_id",
      "clock_time"
    ],
    "additionalProperties": false,
    "allOf": [
      {
        "if": {
          "properties": {
            "ok": {
              "const": false
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "const": "failed"
            },
            "data": {
              "type": "null"
            },
            "error": {
              "$ref": "https://homebench.example/spec/0.2/types.schema.json#/$defs/Error",
              "description": "错误。"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "ok": {
              "const": true
            }
          }
        },
        "then": {
          "properties": {
            "status": {
              "enum": [
                "succeeded",
                "pending",
                "running"
              ]
            },
            "data": {
              "not": {
                "type": "null"
              }
            },
            "error": {
              "type": "null"
            }
          }
        }
      }
    ]
  }
}
```
