#version 430 core

in vec3 v_color;
in vec2 v_texcoord;
in vec3 v_rgb;
in float v_alpha;
in vec2 v_view_size;
in float v_inv_depth;

out vec4 FragColor;

uniform sampler2D u_texture;

void main()
{
    vec2 uv = v_texcoord / v_inv_depth;
    vec4 texColor = texture(u_texture, uv);

    float t = min(1.0, max(0.0, uv.y * 6.56 - 0.72));
    
    texColor.xyz *= min(1.0, 9.5 - uv.y / .02);
    
    texColor.xyz *= min(1.0, gl_FragCoord.x / 1000.0);
    texColor.xyz *= min(1.0, -(gl_FragCoord.x - v_view_size.x) / 1000.0);

    texColor.xyz = mix(vec3(25.0 / 255.0, 15.0 / 255.0, 10.0 / 255.0), texColor.xyz, vec3(t, t, t));
    
    FragColor = texColor * vec4(v_color * v_rgb, v_alpha);
}