$content = @'
{
  "name": "聊天室",
  "id": "chatroom",
  "author": "heweile",
  "version": "1.0",
  "level": 1,
  "description": "MoviePilot在线聊天室，支持实时聊天、表情和在线状态显示",
  "icon": "chat_bubble",
  "main": "chatroom",
  "reload": true,
  "installed": true,
  "scope": [],
  "history": {
    "v1.0": "首次发布，支持在线聊天功能，表情符号，在线状态和链接自动识别"
  }
}
'@

Out-File -FilePath package.json -Encoding utf8 -InputObject $content 