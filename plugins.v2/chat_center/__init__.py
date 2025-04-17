import os
import time
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta

# V2版本导入
from app.plugins.plugin_base import _PluginBase
from app.core.config import settings
from app.log import logger
from app.schemas.types import MediaType, NotificationType


class ChatCenter(_PluginBase):
    # 插件名称
    plugin_name = "聊天中心"
    # 插件描述
    plugin_desc = "多功能聊天室，支持实时交流、表情和在线状态显示"
    # 插件图标
    plugin_icon = "chatroom.svg"
    # 插件版本
    plugin_version = "1.2"
    # 插件作者
    plugin_author = "heweile"
    # 作者主页
    author_url = "https://github.com/heweile"
    # 插件配置项ID前缀
    plugin_config_prefix = "chat_center_"
    # 加载顺序
    plugin_order = 1
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _chat_data_path = None
    _messages = []
    _online_users = {}  # 用户在线状态 {"username": 上次活跃时间戳}
    _max_messages = 100
    _online_timeout = 300  # 用户在线超时时间，单位秒

    def init_plugin(self, config: dict = None):
        """
        插件初始化
        """
        # 设置聊天数据保存路径
        self._chat_data_path = os.path.join(settings.CONFIG_PATH, 'chat_center_data.json')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self._chat_data_path), exist_ok=True)
        
        # 加载配置
        if config:
            if config.get('max_messages'):
                try:
                    self._max_messages = int(config.get('max_messages'))
                except Exception as e:
                    logger.error(f"加载配置失败: {str(e)}")
            if config.get('online_timeout'):
                try:
                    self._online_timeout = int(config.get('online_timeout'))
                except Exception as e:
                    logger.error(f"加载配置失败: {str(e)}")

        # 加载聊天记录
        self._load_messages()
        logger.info(f"聊天中心插件初始化完成")

    def get_api(self) -> List[dict]:
        """
        注册插件API
        """
        return [
            {
                "path": "/messages",
                "endpoint": self.get_messages,
                "methods": ["GET"],
                "summary": "获取聊天消息",
                "description": "获取最近的聊天消息记录"
            },
            {
                "path": "/send",
                "endpoint": self.send_message,
                "methods": ["POST"],
                "summary": "发送聊天消息",
                "description": "发送一条聊天消息"
            },
            {
                "path": "/online",
                "endpoint": self.get_online_users,
                "methods": ["GET"],
                "summary": "获取在线用户",
                "description": "获取当前在线的用户列表"
            },
            {
                "path": "/heartbeat",
                "endpoint": self.user_heartbeat,
                "methods": ["POST"],
                "summary": "用户心跳",
                "description": "更新用户在线状态"
            },
            {
                "path": "/clear",
                "endpoint": self.clear_messages,
                "methods": ["POST"],
                "summary": "清空聊天记录",
                "description": "清空所有聊天记录"
            }
        ]

    def get_messages(self, **kwargs):
        """
        获取聊天消息API
        """
        return {
            "code": 0,
            "message": "操作成功",
            "data": self._messages
        }

    def send_message(self, username=None, content=None, type="text", **kwargs):
        """
        发送聊天消息API
        """
        if not username or not content:
            return {
                "code": 1,
                "message": "用户名和消息内容不能为空！"
            }

        # 更新用户在线状态
        self._update_user_online(username)

        # 创建新消息
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_message = {
            "id": int(time.time() * 1000),
            "username": username,
            "content": content,
            "time": current_time,
            "type": type
        }
        
        # 添加到消息列表
        self._messages.append(new_message)
        
        # 如果消息超过最大数量，删除最早的消息
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]
        
        # 保存消息
        self._save_messages()
        
        return {
            "code": 0,
            "message": "发送成功",
            "data": new_message
        }

    def get_online_users(self, **kwargs):
        """
        获取在线用户API
        """
        # 清理过期的在线用户
        self._clean_offline_users()
        
        # 获取在线用户列表
        online_users = list(self._online_users.keys())
        
        return {
            "code": 0,
            "message": "操作成功",
            "data": online_users
        }

    def user_heartbeat(self, username=None, **kwargs):
        """
        用户心跳API，更新用户在线状态
        """
        if not username:
            return {
                "code": 1,
                "message": "用户名不能为空！"
            }
        
        # 更新用户在线状态
        self._update_user_online(username)
        
        return {
            "code": 0,
            "message": "操作成功"
        }

    def clear_messages(self, **kwargs):
        """
        清空聊天记录API
        """
        self._messages = []
        self._save_messages()
        
        return {
            "code": 0,
            "message": "清空成功"
        }

    def _update_user_online(self, username):
        """
        更新用户在线状态
        """
        if not username:
            return
        
        self._online_users[username] = time.time()

    def _clean_offline_users(self):
        """
        清理离线用户
        """
        now = time.time()
        offline_users = []
        
        for username, last_active in self._online_users.items():
            if now - last_active > self._online_timeout:
                offline_users.append(username)
        
        for username in offline_users:
            self._online_users.pop(username, None)

    def get_pages(self) -> List[dict]:
        """
        注册插件页面
        """
        return [
            {
                "name": "聊天中心",
                "path": "/chat",
                "component": "View",
                "icon": self.plugin_icon,
                "show": True,
                "childs": []
            }
        ]

    def get_state(self) -> bool:
        """
        获取插件状态
        """
        return True

    def get_service(self) -> Optional[Dict[str, Any]]:
        """
        获取插件服务接口
        """
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        获取插件配置表单
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'max_messages',
                                            'label': '最大消息数量',
                                            'placeholder': '保留的最大聊天消息数量，默认100',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'online_timeout',
                                            'label': '在线超时时间(秒)',
                                            'placeholder': '用户在线状态超时时间，默认300秒',
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "max_messages": self._max_messages,
            "online_timeout": self._online_timeout
        }

    def get_page(self) -> List[dict]:
        """
        返回页面配置
        """
        return [
            {
                "component": "div",
                "props": {
                    "class": "pa-4"
                },
                "content": [
                    {
                        "component": "ChatRoom",
                        "props": {
                            "apiMessages": "/api/plugin/chat_center/messages",
                            "apiSend": "/api/plugin/chat_center/send",
                            "apiOnline": "/api/plugin/chat_center/online",
                            "apiHeartbeat": "/api/plugin/chat_center/heartbeat",
                            "apiClear": "/api/plugin/chat_center/clear"
                        }
                    }
                ]
            }
        ]

    def get_page_component(self) -> List[dict]:
        """
        返回页面组件
        """
        return [
            {
                "id": "ChatRoom",
                "name": "ChatRoom",
                "desc": "聊天室组件",
                "template": """
                <div class="chat-room">
                  <v-card>
                    <v-card-title>
                      聊天中心
                      <v-chip class="ml-2" small>在线 {{ onlineUsers.length }} 人</v-chip>
                      <v-spacer></v-spacer>
                      <v-btn icon @click="showEmoji = !showEmoji" class="mr-2">
                        <v-icon>mdi-emoticon-outline</v-icon>
                      </v-btn>
                      <v-btn icon @click="refreshMessages">
                        <v-icon>mdi-refresh</v-icon>
                      </v-btn>
                      <v-menu offset-y>
                        <template v-slot:activator="{ on, attrs }">
                          <v-btn icon v-bind="attrs" v-on="on">
                            <v-icon>mdi-dots-vertical</v-icon>
                          </v-btn>
                        </template>
                        <v-list>
                          <v-list-item @click="showOnlineUsers = true">
                            <v-list-item-title>查看在线用户</v-list-item-title>
                          </v-list-item>
                          <v-list-item @click="confirmClearMessages">
                            <v-list-item-title>清空聊天记录</v-list-item-title>
                          </v-list-item>
                        </v-list>
                      </v-menu>
                    </v-card-title>
                    
                    <v-divider></v-divider>
                    
                    <v-card-text style="height: 400px; overflow-y: auto;" ref="messageContainer">
                      <div v-if="messages.length === 0" class="text-center my-4 text--disabled">
                        暂无消息，发送第一条消息吧！
                      </div>
                      <div v-for="message in messages" :key="message.id" class="message-item py-2">
                        <div class="d-flex">
                          <span class="font-weight-bold primary--text">{{ message.username }}</span>
                          <span class="ml-2 text--disabled text-caption">{{ message.time }}</span>
                        </div>
                        <div v-if="message.type === 'text'" class="ml-2 mt-1" v-html="formatMessageContent(message.content)"></div>
                        <div v-else-if="message.type === 'system'" class="ml-2 mt-1 text--disabled font-italic">{{ message.content }}</div>
                      </div>
                    </v-card-text>
                    
                    <v-divider></v-divider>
                    
                    <div v-if="showEmoji" class="emoji-container pa-2">
                      <v-btn v-for="emoji in emojis" :key="emoji" text small @click="insertEmoji(emoji)" class="emoji-btn">
                        {{ emoji }}
                      </v-btn>
                    </div>
                    
                    <v-card-actions>
                      <v-text-field
                        v-model="username"
                        label="昵称"
                        hide-details
                        dense
                        class="mr-2"
                        style="max-width: 150px;"
                      ></v-text-field>
                      <v-text-field
                        v-model="messageContent"
                        label="输入消息"
                        hide-details
                        dense
                        @keyup.enter="sendMessage"
                      ></v-text-field>
                      <v-btn color="primary" text @click="sendMessage" :disabled="!username || !messageContent">
                        发送
                      </v-btn>
                    </v-card-actions>
                  </v-card>
                  
                  <!-- 在线用户对话框 -->
                  <v-dialog v-model="showOnlineUsers" max-width="300">
                    <v-card>
                      <v-card-title>在线用户 ({{ onlineUsers.length }}人)</v-card-title>
                      <v-card-text>
                        <v-list dense>
                          <v-list-item v-for="user in onlineUsers" :key="user">
                            <v-list-item-icon>
                              <v-icon>mdi-account</v-icon>
                            </v-list-item-icon>
                            <v-list-item-content>
                              <v-list-item-title>{{ user }}</v-list-item-title>
                            </v-list-item-content>
                          </v-list-item>
                        </v-list>
                      </v-card-text>
                      <v-card-actions>
                        <v-spacer></v-spacer>
                        <v-btn text @click="showOnlineUsers = false">关闭</v-btn>
                      </v-card-actions>
                    </v-card>
                  </v-dialog>
                  
                  <!-- 清空确认对话框 -->
                  <v-dialog v-model="showClearConfirm" max-width="300">
                    <v-card>
                      <v-card-title>确认操作</v-card-title>
                      <v-card-text>
                        确定要清空所有聊天记录吗？此操作不可恢复。
                      </v-card-text>
                      <v-card-actions>
                        <v-spacer></v-spacer>
                        <v-btn text @click="showClearConfirm = false">取消</v-btn>
                        <v-btn color="error" text @click="clearMessages">确定</v-btn>
                      </v-card-actions>
                    </v-card>
                  </v-dialog>
                </div>
                """,
                "props": [
                    {
                        "name": "apiMessages",
                        "default": "",
                        "desc": "获取消息的API地址"
                    },
                    {
                        "name": "apiSend",
                        "default": "",
                        "desc": "发送消息的API地址"
                    },
                    {
                        "name": "apiOnline",
                        "default": "",
                        "desc": "获取在线用户的API地址"
                    },
                    {
                        "name": "apiHeartbeat",
                        "default": "",
                        "desc": "发送用户心跳的API地址"
                    },
                    {
                        "name": "apiClear",
                        "default": "",
                        "desc": "清空聊天记录的API地址"
                    }
                ],
                "data": """
                  return {
                    messages: [],
                    onlineUsers: [],
                    username: localStorage.getItem('chatroom_username') || '',
                    messageContent: '',
                    refreshInterval: null,
                    heartbeatInterval: null,
                    showEmoji: false,
                    showOnlineUsers: false,
                    showClearConfirm: false,
                    emojis: ['😀', '😂', '😍', '🤔', '😢', '😎', '👍', '👎', '🎉', '❤️', '🔥', '⭐', '🍕', '🎬', '📺', '🎮', '💾', '💻']
                  }
                """,
                "methods": """
                  async refreshMessages() {
                    try {
                      const response = await fetch(this.apiMessages);
                      const result = await response.json();
                      if (result.code === 0) {
                        this.messages = result.data;
                        this.$nextTick(() => {
                          if (this.$refs.messageContainer) {
                            this.$refs.messageContainer.scrollTop = this.$refs.messageContainer.scrollHeight;
                          }
                        });
                      }
                    } catch (error) {
                      console.error('获取消息失败:', error);
                    }
                  },
                  
                  async refreshOnlineUsers() {
                    try {
                      const response = await fetch(this.apiOnline);
                      const result = await response.json();
                      if (result.code === 0) {
                        this.onlineUsers = result.data;
                      }
                    } catch (error) {
                      console.error('获取在线用户失败:', error);
                    }
                  },
                  
                  async sendMessage() {
                    if (!this.username || !this.messageContent) return;
                    
                    // 保存用户名到本地存储
                    localStorage.setItem('chatroom_username', this.username);
                    
                    try {
                      const response = await fetch(this.apiSend, {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                          username: this.username,
                          content: this.messageContent,
                          type: 'text'
                        })
                      });
                      
                      const result = await response.json();
                      if (result.code === 0) {
                        this.messageContent = '';
                        this.showEmoji = false;
                        await this.refreshMessages();
                        await this.refreshOnlineUsers();
                      }
                    } catch (error) {
                      console.error('发送消息失败:', error);
                    }
                  },
                  
                  async sendHeartbeat() {
                    if (!this.username) return;
                    
                    try {
                      await fetch(this.apiHeartbeat, {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                          username: this.username
                        })
                      });
                    } catch (error) {
                      console.error('发送心跳失败:', error);
                    }
                  },
                  
                  async clearMessages() {
                    try {
                      const response = await fetch(this.apiClear, {
                        method: 'POST'
                      });
                      
                      const result = await response.json();
                      if (result.code === 0) {
                        this.showClearConfirm = false;
                        this.messages = [];
                      }
                    } catch (error) {
                      console.error('清空消息失败:', error);
                    }
                  },
                  
                  confirmClearMessages() {
                    this.showClearConfirm = true;
                  },
                  
                  insertEmoji(emoji) {
                    this.messageContent += emoji;
                  },
                  
                  formatMessageContent(content) {
                    // 将URL转换为可点击链接
                    const urlRegex = /(https?:\\/\\/[^\\s]+)/g;
                    return content.replace(urlRegex, '<a href="$1" target="_blank">$1</a>');
                  }
                """,
                "mounted": """
                  this.refreshMessages();
                  this.refreshOnlineUsers();
                  
                  // 设置自动刷新消息
                  this.refreshInterval = setInterval(() => {
                    this.refreshMessages();
                    this.refreshOnlineUsers();
                  }, 5000); // 每5秒刷新一次
                  
                  // 设置用户心跳
                  this.heartbeatInterval = setInterval(() => {
                    if (this.username) {
                      this.sendHeartbeat();
                    }
                  }, 30000); // 每30秒发送一次心跳
                """,
                "beforeDestroy": """
                  // 清除定时器
                  if (this.refreshInterval) {
                    clearInterval(this.refreshInterval);
                  }
                  if (this.heartbeatInterval) {
                    clearInterval(this.heartbeatInterval);
                  }
                """,
                "styles": """
                .emoji-container {
                  max-height: 100px;
                  overflow-y: auto;
                  display: flex;
                  flex-wrap: wrap;
                  background-color: #f5f5f5;
                }
                .emoji-btn {
                  min-width: 36px !important;
                }
                """
            }
        ]

    def _load_messages(self):
        """
        加载聊天消息
        """
        if os.path.exists(self._chat_data_path):
            try:
                with open(self._chat_data_path, 'r', encoding='utf-8') as f:
                    self._messages = json.load(f)
            except Exception as e:
                logger.error(f"加载聊天记录失败: {str(e)}")
                self._messages = []
        else:
            self._messages = []

    def _save_messages(self):
        """
        保存聊天消息
        """
        try:
            with open(self._chat_data_path, 'w', encoding='utf-8') as f:
                json.dump(self._messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存聊天记录失败: {str(e)}")
