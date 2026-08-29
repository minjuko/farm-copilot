import {
  buildPredictionPayload,
  finiteNumberOrZero,
  normalizePredictionResult,
  removeCropAt,
} from './predictionFlow';

const validInput = {
  landArea: '302.5',
  region: '서울',
  crops: [
    { name: '감자', ratio: '0.4' },
    { name: '고구마', ratio: '0.6' },
  ],
  sessionId: 'session-1',
};

test('keeps crop names and numeric ratios aligned in request order', () => {
  const { payload, error } = buildPredictionPayload(validInput);
  expect(error).toBeUndefined();
  expect(payload).toEqual({
    land_area: 302.5,
    crop_names: ['감자', '고구마'],
    crop_ratios: [0.4, 0.6],
    region: '서울',
    session_id: 'session-1',
  });
  expect(payload.crop_names).toHaveLength(payload.crop_ratios.length);
});

test('removes the crop and its ratio as one item', () => {
  expect(removeCropAt(validInput.crops, 0)).toEqual([{ name: '고구마', ratio: '0.6' }]);
});

test.each(['', '0', '-1', 'not-a-number'])("rejects invalid land area %s", (landArea) => {
  expect(buildPredictionPayload({ ...validInput, landArea }).error).toMatch(/면적/);
});

test.each([
  { crops: [{ name: '감자', ratio: '' }] },
  { crops: [{ name: '감자', ratio: '-1' }, { name: '고구마', ratio: '2' }] },
  { crops: [{ name: '감자', ratio: '0.2' }, { name: '고구마', ratio: '0.2' }] },
  { crops: [{ name: '감자', ratio: '0.3' }, { name: '고구마', ratio: '0.3' }, { name: '양파', ratio: '0.3' }] },
])('rejects invalid crop ratios', ({ crops }) => {
  expect(buildPredictionPayload({ ...validInput, crops }).error).toMatch(/비율/);
});

test('normalizes missing and non-numeric result values without NaN', () => {
  const result = normalizePredictionResult({
    total_income: undefined,
    results: [{ price: null, rmse: 'bad', r2_score: '0.75', adjusted_data: null }],
  });
  expect(result.total_income).toBe(0);
  expect(result.results[0]).toMatchObject({ price: 0, rmse: 0, r2_score: 0.75, adjusted_data: {} });
  expect(Number.isNaN(finiteNumberOrZero(undefined))).toBe(false);
});
