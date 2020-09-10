FROM continuumio/miniconda3:4.8.2

# ARG TASK_REPO="ionlights/ucfai-tasks"

COPY . /tasks

# RUN git clone https://github.com/${TASK_REPO}
RUN conda env create -f /tasks/env.yml

ENV PATH /opt/conda/envs/tasks/bin:$PATH

ENTRYPOINT [ "/tasks/entrypoint.sh" ]