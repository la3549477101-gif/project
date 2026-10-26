package com.example.odmtracker;
import java.time.Duration;
import java.net.URI;
import java.net.http.*;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.http.client.JdkClientHttpRequestFactory;

@Service
public class CustomerArchiveService {
    private final WorkspaceService workspace;
    private final RestClient client;
    public CustomerArchiveService(WorkspaceService workspace,@Value("${odm.flask-api:http://127.0.0.1:5000/api}") String base) {
        this.workspace=workspace;
        HttpClient http=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
        JdkClientHttpRequestFactory factory=new JdkClientHttpRequestFactory(http);
        factory.setReadTimeout(Duration.ofSeconds(5));
        this.client=RestClient.builder().baseUrl(base).requestFactory(factory).build();
    }
    public CustomerRecord ensure(Long id) {
        CustomerRecord c=workspace.customer(id);
        try {
            Map<?,?> response=client.post().uri("/customers/{id}/folder",id).contentType(org.springframework.http.MediaType.APPLICATION_JSON)
                .body(Map.of()).retrieve().body(Map.class);
            String path=response==null?null:(String)response.get("path");
            if(path==null || path.isBlank()) throw new IllegalStateException("文件服务未返回目录");
            return workspace.folderResult(id,path,null);
        } catch(Exception ex) {
            return workspace.folderResult(id,null,"客户已保存，文件夹创建失败。请确认本机文件服务和桌面权限后重试。");
        }
    }
}
