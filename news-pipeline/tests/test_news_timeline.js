const assert = require('node:assert/strict');
const Timeline = require('../../source/news/news-timeline.js');

assert.equal(Timeline.publishedDate({time: '2026-07-11T15:59:00Z'}, '2026-07-11').date, '2026-07-11');
assert.equal(Timeline.publishedDate({time: '2026-07-11T16:00:00Z'}, '2026-07-11').date, '2026-07-12');
assert.deepEqual(Timeline.publishedDate({time: 'bad'}, '2026-07-11'), {date: '2026-07-11', uncertain: true});

const duplicate = [
  {reportDate: '2026-07-12', item: {id: 'pick-1', event_id: 'evt-apple', title: '苹果起诉 OpenAI 窃取商业机密',
    time: '2026-07-12T01:00:00Z', score: 85, sources: [
      {name: 'AI HOT', url: 'https://techcrunch.com/story?utm_source=feed'},
      {name: 'TechCrunch', url: 'https://techcrunch.com/story'}]}},
  {reportDate: '2026-07-11', item: {id: 'pick-2', event_id: 'evt-apple', title: '苹果起诉OpenAI窃取硬件商业机密',
    time: '2026-07-11T01:00:00Z', score: 83, sources: [
      {name: 'BBC', url: 'https://bbc.com/apple-openai'}]}}
];
const grouped = Timeline.groupHotEvents(duplicate);
assert.equal(grouped.length, 1);
assert.equal(grouped[0].sourceCount, 2);
assert.equal(grouped[0].latest.reportDate, '2026-07-12');

const distinct = Timeline.groupHotEvents([
  {reportDate: '2026-07-12', item: {id: 'a', title: 'OpenAI 发布新模型', time: '2026-07-12T01:00:00Z', sources: []}},
  {reportDate: '2026-07-12', item: {id: 'b', title: 'OpenAI 遭遇版权诉讼', time: '2026-07-12T02:00:00Z', sources: []}}
]);
assert.equal(distinct.length, 2);

const sharedDocumentDistinctEvents = Timeline.groupHotEvents([
  {reportDate: '2026-07-23', item: {id: 'data-centre', title: 'OpenAI starts a data-centre project',
    time: '2026-07-23T01:00:00Z', sources: [{name: 'Roundup', url: 'https://example.test/roundup'}]}},
  {reportDate: '2026-07-23', item: {id: 'presence', title: 'OpenAI launches Presence agents',
    time: '2026-07-23T02:00:00Z', sources: [{name: 'Roundup', url: 'https://example.test/roundup'}]}}
]);
assert.equal(sharedDocumentDistinctEvents.length, 2);

const collapsed = Timeline.timelineRows(duplicate);
assert.equal(collapsed.length, 1);
assert.equal(collapsed[0].publishedDate, '2026-07-12');
assert.equal(collapsed[0].item.sources.length, 2);

const progress = Timeline.timelineRows([
  duplicate[1],
  {reportDate: '2026-07-12', item: {...duplicate[0].item,
    title: '苹果与 OpenAI 商业机密案首次开庭', summary: '法院首次审理禁令申请'}}
]);
assert.equal(progress.length, 2);
assert.equal(progress[0].isContinuation, true);

console.log('PASS news timeline helpers');
