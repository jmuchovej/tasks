FROM continuumio/miniconda:4.7.12

# ARG TASK_REPO="ionlights/ucfai-tasks"

COPY entrypoint.sh /entrypoint.sh
COPY . /tasks

# RUN git clone https://github.com/${TASK_REPO}
RUN conda env create -f /tasks/env.yml

ENV PATH /opt/conda/envs/tasks/bin:$PATH

ENTRYPOINT [ "/entrypoint.sh" ]