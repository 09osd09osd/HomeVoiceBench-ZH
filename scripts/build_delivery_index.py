"""Describe local/public delivery without claiming an upload that did not occur."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT / path).read_text('utf-8'))

summary = read('reports/summary.json')
audit = read('reports/release_audit.json')
assets = read('reports/release_assets.json')
publication = read('reports/publication.json') if (ROOT / 'reports/publication.json').exists() else {}
if summary['evaluation_status'] != 'complete' or audit['scope'] != 'complete_release' or audit['status'] != 'passed':
    raise ValueError('Complete audited results required')
if not assets.get('inputs') or not assets.get('evaluation'):
    raise ValueError('Both evidence archive groups are required')
entries = assets['inputs'] + assets['evaluation']
if any(not x['name'].startswith('homevoicebench-zh-v0.3-') for x in entries):
    raise ValueError('Do not mix v0.2 and v0.3 release archives')
if any(not x.get('archive_crc_verified') or not (ROOT / x['path']).is_file() for x in entries):
    raise ValueError('Archive missing or not verified')

repo_url = publication.get('repository_url')
if publication.get('status') == 'published' and publication.get('release_url','').endswith('/v0.3.0'):
    status = '已发布：[' + publication['repository_full_name'] + '](' + repo_url + ')。完整资产见[GitHub Release](' + publication['release_url'] + ')。'
elif repo_url:
    status = '公开仓库：[' + publication['repository_full_name'] + '](' + repo_url + ')。v0.3本地交付已完成，公开发布尚未完成；最终状态以reports/publication.json和GitHub Release为准。'
else:
    status = '本地构建和测评已完成；GitHub尚未发布。本机缺少可用GitHub登录凭据，公开仓库创建与上传已经得到用户授权。'
def download_url(name, local_path):
    return repo_url + '/releases/download/v0.3.0/' + name if repo_url else '../' + local_path
source_link = download_url('homevoicebench-zh-v0.3-source.zip', 'release_parts/homevoicebench-zh-v0.3-source.zip')
intro = '''# 交付包与使用说明

{status}

数据规模：50场景、1,000题、{input_count}段去重输入语音；三个系统共3,000条最终运行记录，其中{judged_count}题有实际回答音频并接受听音评分。其余无回答音频的执行失败计入严格通过率分母，维度分数留空。

首次浏览请打开[说明网页](index.html)、[Excel总览](../outputs/homevoicebench-v030-20261117/HomeVoiceBench-ZH.xlsx)或[结果报告](RESULTS.md)。现有项目目录已经包含所有文件，无需再次解压。

## 搬到另一台电脑

1. 将代码/文本包 `homevoicebench-zh-v0.3-source.zip` 解压到一个新目录；GitHub发布后也可直接克隆仓库。
2. 将输入包和所有evaluation包解压到同一个目录，保留内部相对路径。每个ZIP独立完整，不是需要拼接的分卷压缩文件。
3. 打开 `docs/index.html` 浏览，打开 `outputs/homevoicebench-v030-20261117/HomeVoiceBench-ZH.xlsx` 查看表格。完整运行记录在 `runs/<system>/<case>.json`，其中音频路径相对项目根目录。
4. 需要重新运行模型时按[复现说明](REPRODUCIBILITY.md)安装依赖并配置模型与API。模型权重、密钥和本机环境不包含在交付包中。

代码包包含程序、冻结文本题目、工具合同、字段字典、报告、Excel、HTML及网页试听样例。输入包包含正式输入WAV以及仍被历史/QC元数据引用的缓存；正式输入只计data/manifest.json中的1,650段。evaluation包包含正式回答WAV、逐题轨迹、真实ASR、判官原始响应及保留的修复/试验历史；正式统计只读取三个系统的当前记录，归档历史不混入分数。

## 归档列表

代码包：[homevoicebench-zh-v0.3-source.zip]({source_link})。其SHA256在本地 `reports/source_archive.json` 和 `release_parts/SHA256SUMS.txt`，发布时也提供独立SHA256SUMS.txt；不把代码包自身的哈希嵌入其内部。

| 文件 | 大小 MiB | SHA256 |
|---|---:|---|
'''.format(status=status, source_link=source_link,input_count=summary['dataset']['referenced_verified_unique_audio'],judged_count=sum(x['judged_count'] for x in summary['systems'] if x['category']=='all'))
rows = ['| [{0}]({1}) | {2:.1f} | `{3}` |'.format(x['name'], download_url(x['name'], x['path']), x['bytes']/1024**2, x['sha256']) for x in entries]
(ROOT / 'docs/DELIVERY.md').write_text(intro + '\n'.join(rows) + '\n\nZIP已检查CRC并记录SHA256。机器审题和听音评分不等于人工审核；结论边界见[来源与限制](PROVENANCE.md)。\n', 'utf-8')

local_entries = list(entries)
source = ROOT / 'reports/source_archive.json'
if source.exists():
    source_record=read('reports/source_archive.json')
    if source_record['name']=='homevoicebench-zh-v0.3-source.zip':local_entries.insert(0,source_record)
local_intro = '# HomeVoiceBench-ZH 完整交付包\n\n' + status + '\n\n先解压source，再把inputs和全部evaluation包解压到同一目录。它们是独立ZIP，无需拼接。已有项目目录的内容与这些包相同，可直接使用。解压后打开docs/index.html或Excel；详细说明见[交付文档](../docs/DELIVERY.md)。\n\n'
local_rows = ['- [{0}]({0})：{1:.1f} MiB；SHA256 `{2}`'.format(x['name'], x['bytes']/1024**2, x['sha256']) for x in local_entries]
(ROOT / 'release_parts/README.md').write_text(local_intro + '\n'.join(local_rows) + '\n', 'utf-8')
(ROOT / 'release_parts/SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in local_entries), 'utf-8')
print(json.dumps({'archives':len(local_entries),'publication_status':publication.get('status','not_published'),'bytes':sum(x['bytes'] for x in local_entries)}))
