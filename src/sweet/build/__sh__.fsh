#version 430 core

in vec2 v_texcoord;
uniform sampler2D uTexture;
out vec4 FragColor;
float alphaThreshold = 0;
float depth = -gl_FragCoord.w;

void main()
{
    vec4 tex = texture(uTexture, v_texcoord);

    FragColor = tex;
    if(tex.a <= alphaThreshold) {
        discard;
    }
}