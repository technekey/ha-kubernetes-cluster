#### High available Kubernetes Cluster provisioner. 

The provided playbooks spawn a Kubernetes cluster fast(one click) without knowing the internals of cluster provisioning. The playbook uses libvert, KVM, kubespray and cloud-init technologies in the backend for provisioning the cluster. 

#### The playbook is currently only supports libvert default network. If you plan to expand it to some other network, feel free to modify the playbooks.

All the default configuration are present in the hostvar file and the user may need to update the file as per their requirements. The hostvar file is well commented to explain each parameters. In an Out of the box installation, the playbook would create the following:

````
- two controller nodes
- three worker nodes
- two load balancers(with keepalived and haproxy configured)
````

The configuration of load balancers can be disabled by setting ````ha_enabled: false```` in the hostvar file. Also, note that if ````ha_enabled: true` is set, then user must provide one spare IP in their libvert's default network to be set as load balancer's Virtual/floating IP. 

##### The following are the required packages for the playbook to work, the playbook will automatically install these packages. (tested for Ubuntu22 host)

````
    - python3-libvirt
    - libvirt-clients
    - virtinst
    - guestfs-tools
    - qemu-utils
    - qemu-kvm
    - cloud-image-utils

````

##### The following ansible collections are also needed:
````
ansible-galaxy collection install community.libvirt
ansible-galaxy collection install community.crypto
````

### Syntax:

#### Create a cluster 
For example, the name of the cluster is **'developement'**: (Optionally tweak the hostvar to tweak the number of worker, controller and loadbalancer nodes, the amount of resources to allocate etc)
````
ansible-playbook cluster-provisioner.yml -e cluster_name=development
#if you want to configure kubespray addons and configuration, this is the time
cd development/kubespray
ansible-playbook -i inventory/development/hosts.yaml --become --become-user=root cluster.yml -u technekey  --private-key ../id_ssh_rsa
````
Read about kubespray advanced configuration [here.](https://technekey.com/kubespray-advanced-configuration-for-a-production-cluster/) 
##### Sample output:
````
virsh list
 Id   Name                              State
-------------------------------------------------
 15   development-kube-controller-1     running
 16   development-kube-controller-2     running
 17   development-kube-worker-1         running
 18   development-kube-worker-2         running
 19   development-kube-worker-3         running
 20   development-kube-loadbalancer-1   running
 21   development-kube-loadbalancer-2   running
````
Note that the cluster is exposed via just one IP(floating IP of the loadbalancer):
````
kubectl cluster-info --kubeconfig inventory/development/artifacts/admin.conf 
Kubernetes control plane is running at https://192.168.122.211:8443

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
````
````
kubectl get node -owide --kubeconfig inventory/development/artifacts/admin.conf 
NAME                            STATUS   ROLES           AGE     VERSION   INTERNAL-IP       EXTERNAL-IP   OS-IMAGE           KERNEL-VERSION      CONTAINER-RUNTIME
development-kube-controller-1   Ready    control-plane   3m51s   v1.24.3   192.168.122.240   <none>        Ubuntu 22.04 LTS   5.15.0-41-generic   containerd://1.6.6
development-kube-controller-2   Ready    control-plane   3m25s   v1.24.3   192.168.122.35    <none>        Ubuntu 22.04 LTS   5.15.0-41-generic   containerd://1.6.6
development-kube-worker-1       Ready    <none>          2m29s   v1.24.3   192.168.122.24    <none>        Ubuntu 22.04 LTS   5.15.0-41-generic   containerd://1.6.6
development-kube-worker-2       Ready    <none>          2m29s   v1.24.3   192.168.122.106   <none>        Ubuntu 22.04 LTS   5.15.0-41-generic   containerd://1.6.6
development-kube-worker-3       Ready    <none>          2m29s   v1.24.3   192.168.122.75    <none>        Ubuntu 22.04 LTS   5.15.0-41-generic   containerd://1.6.6
````

#### Delete a cluster, For example, the name of the cluster is development
Note: ````delete_disk```` is an **optional** boolean extra arg to delete the disk of the VM. This would make VM unrecoverable. 
````
ansible-playbook cluster-delete.yml  -e cluster_to_delete=development -e delete_disk=true
````

#### Stopping the cluster (virsh destroy)

````
ansible-playbook cluster-stop.yml  -e cluster_to_stop=development
````
#### Sample output:

````
virsh list --all
 Id   Name                              State
--------------------------------------------------
 -    development-kube-controller-1     shut off
 -    development-kube-controller-2     shut off
 -    development-kube-loadbalancer-1   shut off
 -    development-kube-loadbalancer-2   shut off
 -    development-kube-worker-1         shut off
 -    development-kube-worker-2         shut off
 -    development-kube-worker-3         shut off
````
#### Start the cluster(virsh start)

````
ansible-playbook cluster-start.yml  -e cluster_to_start=development
````

##### Sample output:

````
virsh list --all
 Id   Name                              State
-------------------------------------------------
 22   development-kube-worker-1         running
 23   development-kube-loadbalancer-1   running
 24   development-kube-loadbalancer-2   running
 25   development-kube-worker-2         running
 26   development-kube-controller-1     running
 27   development-kube-controller-2     running
 28   development-kube-worker-3         running
````


#### NOTE: The playbooks are developed and tested on ````Ubuntu22.04```` with ubuntu22.04 cloud images for kubernetes guest hosts. The behaviour on other host OS may differ. 
