import Vue from 'vue';
import Router from 'vue-router';
import Containers from './components/Containers.vue';
import Ping from './components/Ping.vue';

Vue.use(Router);

export default new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/',
      name: 'Containers',
      component: Containers,
    },
    {
      path: '/ping',
      name: 'Ping',
      component: Ping,
    },
  ],
});
