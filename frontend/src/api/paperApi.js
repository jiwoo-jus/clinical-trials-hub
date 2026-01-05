import api from './index';

/**
 * Get PMC structured information
 * @param {{ pmcid: string; pmid?: string; ref_nctids?: string; page?: number; index?: number }} params
 */
export async function getStructuredInfo(params) {
  const { data } = await api.get('/api/paper/structured_info', { params });
  return data;
}

/**
 * Get CTG detailed information
 * @param {{ nctId: string }} params
 */
export async function getCtgDetail(params) {
  const { data } = await api.get('/api/paper/ctg_detail', { params });
  return data;
}

/**
 * Get PMC full text HTML
 * @param {{ pmcid: string }} params
 */
export async function getPmcFullTextHtml(params) {
  const response = await api.get('/api/paper/pmc_full_text_html', { 
    params,
    responseType: 'text'
  });
  return response.data;
}

/**
 * Check systematic review eligibility criteria for a paper
 * @param {{ pmcid: string; inclusion_criteria: string[]; exclusion_criteria: string[] }} body
 */
export async function checkSystematicReview(body) {
  const { data } = await api.post('/api/paper/check_systematic_review', body);
  return data;
}