# Spin up iqe pod and execute IQE tests in it

# Env vars defined by caller:
#IQE_PLUGINS="plugin1,plugin2" -- pytest plugins to run separated by ","
#IQE_MARKER_EXPRESSION="mymarker" -- pytest marker expression
#IQE_FILTER_EXPRESSION="something AND something_else" -- pytest filter, can be "" if no filter desired
#NAMESPACE="mynamespace" -- namespace to deploy iqe pod into, can be set by 'deploy_ephemeral_env.sh'

#IQE_POD_NAME="iqe-tests"
oc apply -n $NAMESPACE -f $APP_ROOT/deploy/rbac-cji-smoketest.yml


job_name=rbac-smoke-tests-iqe
found=false
end=$((SECONDS+45))

echo "Waiting for Job $job_name to appear"

while [ $SECONDS -lt $end ]; do
    if `oc get job $job_name -n $NAMESPACE >/dev/null 2>&1`; then
        found=true
        break
    fi
    sleep 1
done

if [ "$found" == "false" ] ; then
    echo "Job $job_name failed to appear"
    exit 1
fi

echo "Waiting for Job $job_name to be running"
running=false
pod=""

# The jq magic will find all running pods in the ns and regex on the app name
# Loop over for SECONDS and send back the pod's name once found
while [ $SECONDS -lt $end ]; do
    pod=$(oc get pods -n $NAMESPACE -o json | jq -r '.items[] | select(.status.phase=="Running") | select(.metadata.name|test("$job_name.")) .metadata.name')
    if [[ -n $pod ]]; then
        running=true
        break
    fi
    sleep 1
done

if [ "$running" == "false" ] ; then
    echo "Job $job_name failed to start"
    exit 1
fi

# Pipe logs to background to keep them rolling in jenkins
oc logs -n $NAMESPACE $pod -f &

# Wait for the job to Complete or Fail before we try to grab artifacts
oc wait --timeout=3m --for=condition=Complete -n $NAMESPACE job/$job_name || oc wait --timeout=3m
--for=condition=Failed -n $NAMESPACE job/$job_name

oc cp -n $NAMESPACE $pod:artifacts/ $WORKSPACE/artifacts

echo "copied artifacts from iqe pod: "
ls -l $WORKSPACE/artifacts