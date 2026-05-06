import type { RouteComponent } from 'vue-router';

export const views: Record<
  PageRoute.LastDegreeRouteKey,
  RouteComponent | (() => Promise<{ default: RouteComponent }>)
> = {
  403: () => import('./_builtin/403/index.vue'),
  404: () => import('./_builtin/404/index.vue'),
  500: () => import('./_builtin/500/index.vue'),
  'constant-page': () => import('./_builtin/constant-page/index.vue'),
  login: () => import('./_builtin/login/index.vue'),
  'not-found': () => import('./_builtin/not-found/index.vue'),
  about: () => import('./about/index.vue'),
  dashboard_analysis: () => import('./dashboard/analysis/index.vue'),
  dashboard_workbench: () => import('./dashboard/workbench/index.vue'),
  document_naive: () => import('./document/naive/index.vue'),
  'document_project-link': () => import('./document/project-link/index.vue'),
  document_project: () => import('./document/project/index.vue'),
  document_vite: () => import('./document/vite/index.vue'),
  document_vue: () => import('./document/vue/index.vue')
};
