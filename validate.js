// Validation + JSON dump for the exercises array
var req = ['id','source','name','time','duration','group','types','description','materials','steps','purpose','business','format','intensity','contact','tip','adapt','takeaway','audience'];
var validFormat = ['ledokol','energizer','reflection','activity','facilitation'];
var validSource = ['rzd','kipnis','eremeeva','world','facilitation'];
var validTypes = ['energy','team','comm','focus','creative','pro'];
var bad = 0;

exercises.forEach(function (e) {
  req.forEach(function (k) {
    if (!(k in e)) { console.log('MISSING FIELD', e.id, k); bad++; }
  });
  if (!Array.isArray(e.types) || !e.types.length) { console.log('BAD types', e.id); bad++; }
  else e.types.forEach(function (t) { if (!validTypes.includes(t)) { console.log('UNKNOWN type', e.id, t); bad++; } });
  if (!Array.isArray(e.materials)) { console.log('BAD materials', e.id); bad++; }
  if (!Array.isArray(e.steps) || e.steps.length < 3) { console.log('TOO FEW steps', e.id, (e.steps || []).length); bad++; }
  if (!['morning','afternoon','evening'].includes(e.time)) { console.log('BAD time', e.id, e.time); bad++; }
  if (!validFormat.includes(e.format)) { console.log('BAD format', e.id, e.format); bad++; }
  if (!validSource.includes(e.source)) { console.log('BAD source', e.id, e.source); bad++; }
  if (![1,2,3].includes(e.intensity)) { console.log('BAD intensity', e.id, e.intensity); bad++; }
  if (typeof e.contact !== 'boolean') { console.log('BAD contact', e.id, e.contact); bad++; }
  if (e.format === 'facilitation' && (!e.tip || !e.adapt || !e.takeaway)) { console.log('THIN facilitation meta', e.id); bad++; }
  if (!['small','medium','large'].includes(e.group)) { console.log('BAD group', e.id, e.group); bad++; }
  // состав целевой аудитории: 'any' — подходит любой группе,
  // 'mixed' — в однородной группе контакт нужно заменить
  if (!['any','mixed'].includes(e.audience)) { console.log('BAD audience', e.id, e.audience); bad++; }
  if (e.audience === 'mixed' && !e.audienceNote) { console.log('NO audienceNote', e.id); bad++; }
  // facilitation tools are whole events, so they run far longer than a warm-up
  const maxDur = e.format === 'facilitation' ? 180 : 30;
  if (typeof e.duration !== 'number' || e.duration < 3 || e.duration > maxDur) { console.log('BAD duration', e.id, e.duration); bad++; }
  if (!e.name || e.name.length < 3) { console.log('BAD name', e.id); bad++; }
  if (!e.business || e.business.length < 20) { console.log('THIN business', e.id); bad++; }
  if (!e.purpose || e.purpose.length < 20) { console.log('THIN purpose', e.id); bad++; }
  if (!e.description || e.description.length < 40) { console.log('THIN description', e.id); bad++; }
});

var ids = exercises.map(function (e) { return e.id; });
var contiguous = ids.every(function (v, i) { return v === i + 1; });
if (!contiguous) { console.log('IDS NOT CONTIGUOUS'); bad++; }

var seen = {}, dup = 0;
exercises.forEach(function (e) {
  var k = e.name.toLowerCase().trim();
  if (seen[k]) { console.log('DUPLICATE NAME', e.id, e.name); dup++; }
  seen[k] = 1;
});

function tally(key) {
  var o = {};
  exercises.forEach(function (e) {
    var v = typeof key === 'function' ? key(e) : e[key];
    o[v] = (o[v] || 0) + 1;
  });
  return o;
}

var types = {};
exercises.forEach(function (e) { e.types.forEach(function (t) { types[t] = (types[t] || 0) + 1; }); });

console.log('---');
console.log('total:', exercises.length, '| errors:', bad, '| dup names:', dup);
console.log('by time:  ', JSON.stringify(tally('time')));
console.log('by group: ', JSON.stringify(tally('group')));
console.log('by source:', JSON.stringify(tally('source')));
console.log('by type:  ', JSON.stringify(types));
require('fs').writeFileSync('/tmp/exercises.json', JSON.stringify(exercises, null, 2));
console.log('wrote /tmp/exercises.json');
