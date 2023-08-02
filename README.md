# ICP-Checker

一个简单的API，用于查询网站或企业的ICP备案信息。

适用于2023年新版的`工信部ICP/IP地址/域名信息备案管理系统`。

演示网站：https://icp.openeasm.org/query/qianxin.com

注意：演示网站不提供任何SLA保证。
# 特征

✅ 通过 `https://beian.miit.gov.cn/` 查询信息，确保与管局实际信息一致；

✅ 支持通过域名、公司名、备案号查询备案信息

✅ 支持自动完成拖动验证，存在极低的失败率

✅ 支持循环翻页查询，获取查询到的所有备案信息

🆕 使用API提供服务，便于集成

🆕 提供Cache且默认开启，避免对源站产生较大压力

# 输入
```bash
python3 ICP-Checker.py 
```
1. 查询单个域名的备案信息（仅fld，不可含子域名）
```bash
➜  ~ curl http://127.0.0.1:5001/query/qianxin.com | jq

{
  "code": 200,
  "data": [
    {
      "domain_approve_date": "2022-11-21 13:56:30",
      "domain_content_approved": "无",
      "domain_licence": "京ICP备16020626号",
      "domain_name": "qianxin.com",
      "domain_owner": "奇安信科技集团股份有限公司",
      "domain_status": "否",
      "domain_type": "企业",
      "website_licence": "京ICP备16020626号-8"
    }
  ],
  "msg": "success"
}
```
2. 查询单个企业的备案信息
```bash
➜  ~ curl http://127.0.0.1:5001/query/奇安信科技集团股份有限公司 | jq
{
  "code": 200,
  "data": [
    {
      "domain_approve_date": "2022-11-21 13:56:30",
      "domain_content_approved": "无",
      "domain_licence": "京ICP备16020626号",
      "domain_name": "tianfucup.com",
      "domain_owner": "奇安信科技集团股份有限公司",
      "domain_status": "否",
      "domain_type": "企业",
      "website_licence": "京ICP备16020626号-14"
    },
    {
      "domain_approve_date": "2022-11-21 13:56:30",
      "domain_content_approved": "无",
      "domain_licence": "京ICP备16020626号",
      "domain_name": "secmp.net",
      "domain_owner": "奇安信科技集团股份有限公司",
      "domain_status": "否",
      "domain_type": "企业",
      "website_licence": "京ICP备16020626号-2"
    },
...
```
3. 查询备案号信息
输入备案号查询信息，如："粤B2-20090059-5"、"浙B2-20080224-1"、"京ICP证030173号-1"等，如果不带结尾"-数字"，则会将该证名下所有域名查询出来。
```bash
➜  ~ curl http://127.0.0.1:5001/query/京ICP备16020626号 | jq
{
  "code": 200,
  "data": [
    {
      "domain_approve_date": "2022-11-21 13:56:30",
      "domain_content_approved": "无",
      "domain_licence": "京ICP备16020626号",
      "domain_name": "tianfucup.com",
      "domain_owner": "奇安信科技集团股份有限公司",
      "domain_status": "否",
      "domain_type": "企业",
      "website_licence": "京ICP备16020626号-14"
...
```

# 缓存说明
默认24小时。 如果命中缓存，在response中会有`"cached": true`的标记位。
在URL中添加`no_cache`可强制刷新缓存。
```bash
curl http://127.0.0.1:5001/query/qianxin.com?no_cache=1 | jq
```

# 说明

⚠ 项目仅用于学习交流，不可用于商业及非法用途。

# 依赖

`pip install -r requirements.txt`

 