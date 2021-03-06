from detecta import *
from ssh_connect import *
import os
import re
import netifaces as ni
import json

def conexiones_router(ip, ip_conexion,user="admin",password="admin01",secret="1234"):
    #Prototipo de conexion
    cisco={
        "device_type":"cisco_xe",
        "ip":ip,
        "username":user,
        "password":password,
        "secret":secret
    }
    cmd = ["traceroute " + ip_conexion]
    salida = conectar(cisco, cmd)
    return salida[0].split('\n\n')[1].split(' ')[3]



def scan_by_interface(interface_name="tap0",user="admin",password="admin01",secret="1234"):
    conexiones_pc = {}
    # Prototipo de conexión a router cisco
    cisco={
        "device_type":"cisco_xe",
        "ip":"",
        "username":user,
        "password":password,
        "secret":secret
    }
    # Obtienen el disccionario de los datos de la red
    dic_data=ni.ifaddresses(interface_name)
    if 2 not in dic_data:
        #print("No hay una dirección IPv4 en la interfaz")
        return [-1,-1]
    dic_data=dic_data[2][0]
    print(f"\n---------About---------\n{interface_name}:{dic_data}")
    addr=list(map(int,dic_data["addr"].split(".")))
    net=list(map(int,dic_data["netmask"].split(".")))

    c=determinate_prefix(net)
    # Se obtiene el identificador de la subred
    idnet=get_id_net(addr,net)
    # Se obtiene la dirección de broadcast
    range_net=get_broadcast_ip(idnet,net)

    #print(f"-------Scan Network:-------\n\tID: {arr_to_ip(idnet)}/{c}\n\tNetmask: {arr_to_ip(net)}\n\tBroadcast: {arr_to_ip(range_net)}")

    # Se prepara para hacer is_host_up
    ips=[idnet[0],idnet[1],idnet[2],idnet[3]+1]
    responde=scan_range(ips,range_net)
    #print(f"de la ip {ips} con rango {range_net} responde {responde}")

    # Se filtra por primera vez que solo los elementos que sean Cisco

    ciscos=[]
    for i in range(len(responde)):
        for k,v in responde[i].items():
            if "Cisco_Router_IOS" in v:

                responde[i][k] = "R" + responde[i][k][len(responde[i][k])-1]
                ciscos.append(responde[i])
            else:
                conexiones_pc[k] = {"name":responde[i][k], "conexiones":[f"{idnet[0]}.{idnet[1]}.{idnet[2]}.{idnet[3]+1}"]}

    ##print(f"Solo routers cisco: {ciscos}")

    # Despues de todo lo que hace el modulo hay que conectarse por ssh o telnet
    #   a los dispositivos cisco
    cmd=["sh ip int | i Internet address","sh ip int br | include up","sh run | include hostname"]
    c=0
    red={}
    net_router={}
    for i in ciscos:
        flag=False
        # Los datos del router (Interfaces)
        for k,v in i.items():
            print(f"-------Enviando comandos a router con ip: {k}-------")
            cisco["ip"]=k
            output=conectar(cisco,cmd)
            dir=re.split("\n|  Internet address is | ",output[0])
            inte=re.split("\n|      YES NVRAM  up                    up      |      YES manual up                    up  | ",output[1])
            host_cmd=output[2].split("hostname ")[1]
            direcciones=[]
            interf=[]
            for j in dir:
                if j!="":
                    direcciones.append(j)
            for j in inte:
                if j!="":
                    interf.append(j)
            if host_cmd in red.keys():
                flag=False
            else:
                flag=True
            if flag:
                iter={}
                for j in range(len(direcciones)):
                    iter[interf[(j*2)]]=direcciones[j]
                red[host_cmd]=iter
            dir.clear()
            inte.clear()
            direcciones.clear()
        # Scan de subredes del router
        if flag:
            for k,v in red.items():
                if 0 not in v.values():
                    #print(type(v))
                    for j,l in v.items():
                        red_e=l.split("/")
                        #print("estoy diviendo a {} y j es {}".format(l, j))
                        if red_e[0] in i.keys():
                            pass
                        elif l == 'Internet' or l== 'is':
                           pass
                        else:
                            net=create_masc_by_prefix(int(red_e[1]))
                            id=get_id_net(list(map(int,red_e[0].split("."))),net)
                            br=get_broadcast_ip(id,net)
                            ip=[id[0],id[1],id[2],id[3]+1]
                            print(f"-------Scan Network:-------\n\tID: {arr_to_ip(id)}\n\tNetmask: {arr_to_ip(net)}\n\tBroadcast: {arr_to_ip(br)}")
                            resp_r=scan_range(ip,br)
                            print(f"De este analisis obtuvimos respuesta de {resp_r}")
                            responde=responde+resp_r
                            # aca filtrar Equipos cisco
                            for a in range(len(resp_r)):
                                for b,d in resp_r[a].items():
                                    if "Cisco_Router_IOS" in d:
                                        resp_r[a][b] = "R" + resp_r[a][b][len(resp_r[a][b])-1]
                                        #print(resp_r[a])
                                        ciscos.append(resp_r[a])
                                    else:
                                        conexiones_pc[b] = {"name":resp_r[a][b], "conexiones":[f"{id[0]}.{id[1]}.{id[2]}.{id[3]+1}"]}
                    net_router[k]=v
                red[k]={0:0}
    json_respond=json.dumps(responde,sort_keys=True,indent=4)
    json_routers=json.dumps(net_router,sort_keys=True,indent=4)
    #print(f"Host con respuesta:\n{json_respond}")
    #print(f"Diccionario de routers:\n{json_routers}")
    return [responde,conexiones_pc]
