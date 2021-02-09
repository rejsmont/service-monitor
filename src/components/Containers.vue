<template>
  <div class="container">
    <div class="row">
      <div class="col-sm-4">
        <h1>Containers</h1>
        <div class="card">
          <template v-for="(instances, location) in containers">
            <a v-b-toggle="'collapse-' + location" class="card-header list-group-item-action">
              <i class="fas fa-server"></i>&nbsp;&nbsp;{{ location }}
              <template v-if="counts[location].running > 0">
                <span class="badge badge-pill badge-success float-right">
                  {{ counts[location].running }}
                </span>
                <span class="float-right">&nbsp;</span>
              </template>
              <template v-if="counts[location].stopped > 0">
                <span class="badge badge-pill badge-secondary float-right">
                  {{ counts[location].stopped }}
                </span>
                <span class="float-right">&nbsp;</span>
              </template>
              <template v-if="counts[location].errored > 0">
                <span class="float-right">&nbsp;</span>
                <span class="badge badge-pill badge-secondary float-right">
                  {{ counts[location].errored }}
                </span>
                <span class="float-right">&nbsp;</span>
              </template>
            </a>
            <b-collapse v-bind:id="'collapse-' + location" class="list-group list-group-flush"
                        v-bind:key="location">
                <a v-for="(status, instance) in instances" v-bind:key="instance"
                    class="list-group-item-action list-group-item py-1" >
                  <div class="d-flex w-100 justify-content-between">
                    <small><i class="fas fa-cube"></i>&nbsp;&nbsp;{{ instance }}</small>
                    <span v-if="status === 'running'" class="badge badge-success">
                      running
                    </span>
                    <span v-else-if="status === 'stopped'" class="badge badge-secondary">
                      stopped
                    </span>
                    <span v-else class="badge badge-danger">
                      error
                    </span>
                  </div>
                </a>
            </b-collapse>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      containers: [],
      counts: [],
    };
  },
  methods: {
    getContainers() {
      const path = 'http://localhost:5000/containers';
      axios.get(path)
        .then((res) => {
          this.containers = res.data.containers;
          this.counts = {};
          Object.keys(this.containers).forEach((location) => {
            this.counts[location] = {};
            this.counts[location].running = 0;
            this.counts[location].stopped = 0;
            this.counts[location].errored = 0;
            Object.values(this.containers[location]).forEach((status) => {
              this.counts[location][status] += 1;
            });
          });
        })
        .catch((error) => {
          // eslint-disable-next-line
          console.error(error);
        });
    },
  },
  created() {
    this.getContainers();
  },
};
</script>

<style scoped>

</style>
